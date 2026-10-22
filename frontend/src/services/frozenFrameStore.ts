const DATABASE_NAME = "aeroguard-local-cache";
const DATABASE_VERSION = 1;
const STORE_NAME = "frozen-camera-frames";

export interface FrozenFrameRecord {
  userId: string;
  cameraId: string;
  blob: Blob;
  capturedAt: number;
}

let databasePromise: Promise<IDBDatabase> | null = null;

const openDatabase = () => {
  if (databasePromise) return databasePromise;

  databasePromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, {
          keyPath: ["userId", "cameraId"],
        });
      }
    };
    request.onsuccess = () => {
      const database = request.result;
      database.onversionchange = () => {
        database.close();
        databasePromise = null;
      };
      resolve(database);
    };
    request.onerror = () => {
      databasePromise = null;
      reject(request.error ?? new Error("Failed to open frozen-frame storage"));
    };
    request.onblocked = () => {
      databasePromise = null;
      reject(new Error("Frozen-frame storage upgrade was blocked"));
    };
  });

  return databasePromise;
};

export const saveFrozenFrame = async (record: FrozenFrameRecord) => {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(record);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("Failed to save frozen frame"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("Saving frozen frame was aborted"));
  });
};

export const getFrozenFramesForUser = async (userId: string) => {
  const database = await openDatabase();
  return new Promise<FrozenFrameRecord[]>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const range = IDBKeyRange.bound(
      [userId, ""],
      [userId, "\uffff"],
    );
    const request = transaction.objectStore(STORE_NAME).getAll(range);
    request.onsuccess = () => resolve(request.result as FrozenFrameRecord[]);
    request.onerror = () =>
      reject(request.error ?? new Error("Failed to load frozen frames"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("Loading frozen frames was aborted"));
  });
};

export const deleteFrozenFrame = async (userId: string, cameraId: string) => {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).delete([userId, cameraId]);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("Failed to delete frozen frame"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("Deleting frozen frame was aborted"));
  });
};
