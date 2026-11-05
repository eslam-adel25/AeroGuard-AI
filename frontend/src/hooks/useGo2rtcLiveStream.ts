import { useEffect, useState } from "react";

export type LiveStreamStatus =
  | "connecting"
  | "stream unavailable"
  | "playback initialization failed"
  | "codec unsupported"
  | "WebRTC connection failed"
  | "playing";

const WEBRTC_TIMEOUT_MS = 8000;
const INITIAL_RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_DELAY_MS = 30000;
const MAX_PENDING_MSE_CHUNKS = 24;
const MSE_CODECS =
  "avc1.640029,avc1.64002A,avc1.640033,mp4a.40.2,mp4a.40.5,flac,opus";

function getGo2rtcBaseUrl() {
  const configured = import.meta.env.VITE_GO2RTC_BASE_URL as
    | string
    | undefined;
  const baseUrl =
    configured?.trim() ||
    new URL("/go2rtc", window.location.origin).href;
  const parsed = new URL(baseUrl);
  if (
    window.location.protocol === "https:" &&
    parsed.protocol !== "https:"
  ) {
    throw new Error("go2rtc must use HTTPS when the Dashboard uses HTTPS");
  }
  return parsed.href.replace(/\/$/, "");
}

function createSignalingUrl(cameraId: string) {
  const base = new URL(getGo2rtcBaseUrl());
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `${base.pathname.replace(/\/$/, "")}/api/ws`;
  base.search = new URLSearchParams({ src: cameraId }).toString();
  base.hash = "";
  return base.href;
}

export function useGo2rtcLiveStream(
  video: HTMLVideoElement | null,
  cameraId: string | null,
): LiveStreamStatus {
  const [status, setStatus] = useState<LiveStreamStatus>("stream unavailable");

  useEffect(() => {
    if (!video || !cameraId) {
      setStatus("stream unavailable");
      return;
    }
    const activeVideo = video;
    const activeCameraId = cameraId;

    let disposed = false;
    let fallbackStarted = false;
    let hasReceivedTrack = false;
    let signalingSocket: WebSocket | null = null;
    let mseSocket: WebSocket | null = null;
    let peerConnection: RTCPeerConnection | null = null;
    let mediaSource: MediaSource | null = null;
    let sourceBuffer: SourceBuffer | null = null;
    let mediaObjectUrl: string | null = null;
    let mseCanPlayHandler: (() => void) | null = null;
    let noVideoTimer: number | null = null;
    let retryTimer: number | null = null;
    let mseTimeout: number | null = null;
    let reconnectAttempts = 0;
    let pendingMseChunks: ArrayBuffer[] = [];
    let pendingRemoteCandidates: RTCIceCandidateInit[] = [];
    let pendingLocalCandidates: string[] = [];
    let offerSent = false;
    let mseMimeType: string | null = null;

    const updateStatus = (next: LiveStreamStatus) => {
      if (!disposed) setStatus(next);
    };

    const closePeerConnection = () => {
      if (signalingSocket) {
        signalingSocket.onopen = null;
        signalingSocket.onmessage = null;
        signalingSocket.onerror = null;
        signalingSocket.onclose = null;
        signalingSocket.close();
        signalingSocket = null;
      }
      if (peerConnection) {
        peerConnection.ontrack = null;
        peerConnection.onicecandidate = null;
        peerConnection.onconnectionstatechange = null;
        peerConnection.close();
        peerConnection = null;
      }
      if (activeVideo.srcObject) activeVideo.srcObject = null;
    };

    const closeMse = () => {
      if (mseSocket) {
        mseSocket.onopen = null;
        mseSocket.onmessage = null;
        mseSocket.onerror = null;
        mseSocket.onclose = null;
        mseSocket.close();
        mseSocket = null;
      }
      if (
        mediaSource &&
        mediaSource.readyState === "open" &&
        sourceBuffer &&
        !sourceBuffer.updating
      ) {
        try {
          mediaSource.endOfStream();
        } catch {
          console.debug("go2rtc MSE source was already closed", cameraId);
        }
      }
      sourceBuffer = null;
      mediaSource = null;
      pendingMseChunks = [];
      mseMimeType = null;
      if (mseCanPlayHandler) {
        activeVideo.removeEventListener("canplay", mseCanPlayHandler);
        mseCanPlayHandler = null;
      }
      if (mseTimeout !== null) {
        window.clearTimeout(mseTimeout);
        mseTimeout = null;
      }
      if (mediaObjectUrl) {
        URL.revokeObjectURL(mediaObjectUrl);
        mediaObjectUrl = null;
      }
      if (activeVideo.src) {
        activeVideo.pause();
        activeVideo.removeAttribute("src");
        activeVideo.load();
      }
    };

    const clearNoVideoTimer = () => {
      if (noVideoTimer !== null) {
        window.clearTimeout(noVideoTimer);
        noVideoTimer = null;
      }
    };

    const scheduleReconnect = () => {
      if (disposed || retryTimer !== null) return;
      const delay = Math.min(
        INITIAL_RECONNECT_DELAY_MS * 2 ** reconnectAttempts,
        MAX_RECONNECT_DELAY_MS,
      );
      reconnectAttempts += 1;
      retryTimer = window.setTimeout(() => {
        retryTimer = null;
        fallbackStarted = false;
        hasReceivedTrack = false;
        closePeerConnection();
        closeMse();
        startWebRtc();
      }, delay);
    };

    const appendNextMseChunk = () => {
      if (
        !sourceBuffer ||
        sourceBuffer.updating ||
        pendingMseChunks.length === 0
      ) {
        return;
      }
      try {
        sourceBuffer.appendBuffer(pendingMseChunks.shift()!);
      } catch (error) {
        console.error("go2rtc MSE append failed", {
          cameraId,
          error,
        });
        updateStatus("playback initialization failed");
        closeMse();
        scheduleReconnect();
      }
    };

    const startMseFallback = () => {
      if (disposed || fallbackStarted) return;
      fallbackStarted = true;
      clearNoVideoTimer();
      closePeerConnection();
      closeMse();
      updateStatus("WebRTC connection failed");
      console.warn("go2rtc WebRTC failed; trying MSE fallback", cameraId);
      if (typeof MediaSource === "undefined") {
        updateStatus("codec unsupported");
        scheduleReconnect();
        return;
      }

      let url: string;
      try {
        url = createSignalingUrl(activeCameraId);
      } catch (error) {
        console.error("go2rtc signaling URL is invalid", { cameraId, error });
        updateStatus("stream unavailable");
        scheduleReconnect();
        return;
      }

      try {
        mseSocket = new WebSocket(url);
        mseSocket.binaryType = "arraybuffer";
      } catch (error) {
        console.error("go2rtc MSE connection could not be created", {
          cameraId,
          error,
        });
        updateStatus("stream unavailable");
        scheduleReconnect();
        return;
      }

      let mseStarted = false;
      const failMse = (failure: LiveStreamStatus) => {
        updateStatus(failure);
        closeMse();
        scheduleReconnect();
      };

      mseSocket.onopen = () => {
        mseSocket?.send(JSON.stringify({ type: "mse", value: MSE_CODECS }));
      };

      mseSocket.onmessage = (event: MessageEvent<string | ArrayBuffer>) => {
        if (typeof event.data === "string") {
          let message: { type?: string; value?: string };
          try {
            message = JSON.parse(event.data);
          } catch (error) {
            console.error("go2rtc returned invalid MSE signaling data", {
              cameraId,
              error,
            });
            failMse("playback initialization failed");
            return;
          }
          if (message.type === "error") {
            console.error("go2rtc MSE stream is unavailable", cameraId);
            failMse("stream unavailable");
            return;
          }
          if (message.type !== "mse" || !message.value) return;
          if (!MediaSource.isTypeSupported(message.value)) {
            console.error("Browser does not support go2rtc MSE codec", {
              cameraId,
              mimeType: message.value,
            });
            failMse("codec unsupported");
            return;
          }
          mseMimeType = message.value;
          mediaSource = new MediaSource();
          mediaObjectUrl = URL.createObjectURL(mediaSource);
          activeVideo.srcObject = null;
          activeVideo.src = mediaObjectUrl;
          activeVideo.load();
          mediaSource.addEventListener(
            "sourceopen",
            () => {
              if (!mediaSource || !mseMimeType || disposed) return;
              try {
                sourceBuffer = mediaSource.addSourceBuffer(mseMimeType);
                sourceBuffer.mode = "segments";
                sourceBuffer.addEventListener("updateend", appendNextMseChunk);
                mseStarted = true;
                mseCanPlayHandler = () => {
                  void activeVideo.play().catch((error: unknown) => {
                    console.error("go2rtc MSE playback initialization failed", {
                      cameraId,
                      error,
                    });
                    updateStatus("playback initialization failed");
                  });
                };
                activeVideo.addEventListener(
                  "canplay",
                  mseCanPlayHandler,
                  { once: true },
                );
                appendNextMseChunk();
              } catch (error) {
                console.error("go2rtc MSE source buffer initialization failed", {
                  cameraId,
                  error,
                });
                failMse("playback initialization failed");
              }
            },
            { once: true },
          );
          return;
        }

        if (!(event.data instanceof ArrayBuffer)) return;
        if (pendingMseChunks.length >= MAX_PENDING_MSE_CHUNKS) {
          console.error("go2rtc MSE buffer exceeded its bounded queue", cameraId);
          failMse("playback initialization failed");
          return;
        }
        pendingMseChunks.push(event.data);
        if (mseStarted) appendNextMseChunk();
      };

      mseSocket.onerror = () => {
        console.error("go2rtc MSE WebSocket failed", cameraId);
        failMse("stream unavailable");
      };
      mseSocket.onclose = () => {
        if (!disposed && !retryTimer) {
          console.warn("go2rtc MSE WebSocket closed", cameraId);
          failMse("stream unavailable");
        }
      };
      mseTimeout = window.setTimeout(() => {
        if (!disposed && !mseStarted && mseSocket?.readyState !== WebSocket.CLOSED) {
          failMse("stream unavailable");
        }
      }, WEBRTC_TIMEOUT_MS);
    };

    function startWebRtc() {
      if (disposed) return;
      updateStatus("connecting");
      try {
        signalingSocket = new WebSocket(createSignalingUrl(activeCameraId));
        peerConnection = new RTCPeerConnection();
      } catch (error) {
        console.error("go2rtc WebRTC initialization failed", { cameraId, error });
        startMseFallback();
        return;
      }

      const socket = signalingSocket;
      const peer = peerConnection;
      peer.addTransceiver("video", { direction: "recvonly" });
      peer.ontrack = (event) => {
        hasReceivedTrack = true;
        clearNoVideoTimer();
        activeVideo.srcObject =
          event.streams[0] || new MediaStream([event.track]);
        void activeVideo.play().catch((error: unknown) => {
          console.error("go2rtc WebRTC playback initialization failed", {
            cameraId,
            error,
          });
          updateStatus("playback initialization failed");
          startMseFallback();
        });
      };
      peer.onicecandidate = (event) => {
        if (!event.candidate) return;
        const candidate = event.candidate.candidate;
        if (!candidate) return;
        if (!offerSent) {
          pendingLocalCandidates.push(candidate);
        } else if (socket.readyState === WebSocket.OPEN) {
          socket.send(
            JSON.stringify({ type: "webrtc/candidate", value: candidate }),
          );
        }
      };
      peer.onconnectionstatechange = () => {
        if (peer.connectionState === "failed") startMseFallback();
        if (peer.connectionState === "disconnected") {
          window.setTimeout(() => {
            if (!disposed && peer.connectionState === "disconnected") {
              startMseFallback();
            }
          }, 1500);
        }
      };

      socket.onopen = async () => {
        try {
          const offer = await peer.createOffer();
          if (disposed || socket.readyState !== WebSocket.OPEN) return;
          await peer.setLocalDescription(offer);
          if (!peer.localDescription?.sdp) {
            throw new Error("WebRTC offer did not contain SDP");
          }
          socket.send(
            JSON.stringify({
              type: "webrtc/offer",
              value: peer.localDescription.sdp,
            }),
          );
          offerSent = true;
          for (const candidate of pendingLocalCandidates) {
            socket.send(
              JSON.stringify({ type: "webrtc/candidate", value: candidate }),
            );
          }
          pendingLocalCandidates = [];
          noVideoTimer = window.setTimeout(() => {
            if (!disposed && !hasReceivedTrack) startMseFallback();
          }, WEBRTC_TIMEOUT_MS);
        } catch (error) {
          console.error("go2rtc WebRTC offer negotiation failed", {
            cameraId,
            error,
          });
          startMseFallback();
        }
      };

      socket.onmessage = async (event: MessageEvent<string>) => {
        let message: { type?: string; value?: string };
        try {
          message = JSON.parse(event.data);
        } catch (error) {
          console.error("go2rtc returned invalid WebRTC signaling data", {
            cameraId,
            error,
          });
          startMseFallback();
          return;
        }
        if (message.type === "error") {
          console.error("go2rtc WebRTC signaling reported a stream error", cameraId);
          startMseFallback();
          return;
        }
        try {
          if (message.type === "webrtc/answer" && message.value) {
            await peer.setRemoteDescription({
              type: "answer",
              sdp: message.value,
            });
            for (const candidate of pendingRemoteCandidates) {
              await peer.addIceCandidate(candidate);
            }
            pendingRemoteCandidates = [];
          } else if (
            message.type === "webrtc/candidate" &&
            message.value
          ) {
            const candidate = {
              candidate: message.value,
              sdpMid: "0",
              sdpMLineIndex: 0,
            };
            if (peer.remoteDescription) {
              await peer.addIceCandidate(candidate);
            } else {
              pendingRemoteCandidates.push(candidate);
            }
          }
        } catch (error) {
          console.error("go2rtc WebRTC negotiation failed", { cameraId, error });
          startMseFallback();
        }
      };

      socket.onerror = () => {
        console.error("go2rtc WebRTC signaling connection failed", cameraId);
        startMseFallback();
      };
      socket.onclose = () => {
        if (!disposed && !fallbackStarted) {
          console.warn("go2rtc WebRTC signaling connection closed", cameraId);
          updateStatus("WebRTC connection failed");
          startMseFallback();
        }
      };
    }

    const handlePlaying = () => {
      reconnectAttempts = 0;
      clearNoVideoTimer();
      updateStatus("playing");
    };
    const handleVideoError = () => {
      if (disposed) return;
      console.error("go2rtc video element playback failed", {
        cameraId,
        mediaErrorCode: activeVideo.error?.code,
      });
      updateStatus("playback initialization failed");
      if (!fallbackStarted) startMseFallback();
    };
    activeVideo.addEventListener("playing", handlePlaying);
    activeVideo.addEventListener("error", handleVideoError);
    updateStatus("connecting");
    startWebRtc();

    return () => {
      disposed = true;
      clearNoVideoTimer();
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      if (mseTimeout !== null) window.clearTimeout(mseTimeout);
      activeVideo.removeEventListener("playing", handlePlaying);
      activeVideo.removeEventListener("error", handleVideoError);
      closePeerConnection();
      closeMse();
      activeVideo.pause();
      activeVideo.srcObject = null;
    };
  }, [video, cameraId]);

  return status;
}
