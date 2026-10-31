const en = {
  common: {
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    upload: "Upload",
    undo: "Undo",
    clear: "Clear",
    points: "Points",
    refresh: "Refresh",
    search: "Search",
    filter: "Filter",
    notifications: "Notifications",
    active: "Active",
    recording: "Recording",
    objects: "Objects",
    fps: "FPS",
    alerts: "Alerts",
    close: "Close",
    retry: "Retry",
    loading: "Loading",
    yes: "Yes",
    no: "No",
    language: "Language",
    back: "Back",
    apply: "Apply",
    done: "Done",
    admin: "Administrator",
    status: "Status",
    confirm: "Confirm",
    processing: "Processing",
    pleaseWait: "Please wait...",
    success: "Success",
    operationFailed: "Operation Failed",
    toggleLanguage: "Switch language",
    view: "View",
    download: "Download",
    preview: "Preview",
    load: "Load",
    read: "Read",
    unread: "Unread",
    noData: "No data available",
    noResults: "No results found",
    connected: "Connected",
    disconnected: "Disconnected",
    online: "Online",
    offline: "Offline",
    login: "Log in",
    createAccount: "Create Account",
    forgotPassword: "Forgot?",
    rememberDevice: "Remember this device for 30 days",
    camera: "Camera",
    cameras: "Cameras",
    unknownCamera: "Unknown Camera",
    total: "Total",
    pdf: "PDF",
  },
  app: {
    title: "AeroGuard AI",
    subtitle: "Smart Surveillance Platform",
    dashboardTitle: "AeroGuard Dashboard",
    headerTitle: "AeroGuard Dashboard",
    notifications: {
      title: "Security Notifications",
      empty: "No notifications available yet.",
      markAllRead: "Mark all read",
      clear: "Clear",
      camera: "Camera",
      read: "Read",
      view: "View",
      download: "Download",
      preview: "Preview",
      noNewAlerts: "No new alerts",
    },
  },
  sidebar: {
    monitoring: "Dashboard",
    cameras: "Cameras",
    analytics: "Analytics",
    profile: "Profile",
    control: "Settings",
    logout: "Logout",
    collapse: "Collapse sidebar",
    expand: "Expand sidebar",
  },
  auth: {
    username: "Username",
    password: "Password",
    enterUsername: "Enter your username",
    enterPassword: "Enter your password",
    authorizeAccess: "Authorize Access",
    invalidCredentials: "Invalid credentials. Please try again.",
    secureInfrastructureNode: "Secure Infrastructure Node",
    loginTitle: "AeroGuard AI",
    loginSubtitle: "Smart Surveillance Platform",
    registerTitle: "Operator Registry",
    registerSubtitle: "Provision a new node administrator account",
    fullIdentityName: "Full Identity Name",
    systemUsername: "System Username",
    corporateEmail: "Corporate Email",
    securePhoneLine: "Secure Phone Line",
    masterPassword: "Master Password",
    confirmEncryption: "Confirm Encryption",
    organizationOptional: "Organization (Optional)",
    requestAuthorization: "Request Authorization",
    existingAccount: "Already authorized?",
    establishConnection: "Establish Connection",
    passwordsDoNotMatch: "Passwords do not match",
    registrationSuccess:
      "✅ Registration Successful! Please login with your credentials.",
    registrationFailed: "Registration failed.",
    usernameOrEmailTaken:
      "Registration failed. Username or Email may be taken.",
    avatarUpdated: "✅ Avatar updated!",
    avatarUploadFailed: "❌ Failed to upload image.",
    securityIdentityUpdated: "✅ Security identity updated successfully!",
    profileUpdateFailed: "❌ Failed to update registry.",
    credentialsRotated: "✅ Credentials rotated successfully!",
    passwordMismatch: "❌ New passwords do not match!",
    invalidPassword: "❌ Authentication Error: Current password incorrect.",
    initialSession: "First Session",
    welcomeBack: "Welcome Back",
    welcomeBackSubtitle:
      "Please enter your credentials to access your secure node.",
    heroBadge: "AI-POWERED SMART SURVEILLANCE",
    heroTitle: "Secure Access to",
    heroDescription:
      "Access the AeroGuard AI platform to monitor airports, railway stations, metro systems, and transportation hubs using AI-powered surveillance, real-time alerts, and centralized security management.",
    heroImageAlt: "Surveillance Control Room",
    createAccountTitle: "Create AeroGuard Account",
    createAccountSubtitle:
      "Create your secure AeroGuard AI account to access the intelligent surveillance platform.",
    createAccountLink: "Create Account",
    loginLink: "Log In",
    forgotPassword: "Forgot?",
    rememberDevice: "Remember this device for 30 days",
    noAccount: "Don't have an AeroGuard account?",
    noAccountCta: "Create Account",
    loginButton: "LOG IN",
    fullNameRequired: "Full name is required.",
    usernameRequired: "Username is required.",
    usernameMinLength: "Username must be at least 3 characters.",
    emailRequired: "Corporate email is required.",
    emailInvalid: "Please enter a valid email address.",
    phoneRequired: "Phone number is required.",
    passwordMinLength: "Password must be at least 8 characters.",
    verifyEmailTitle: "Verify Your Email",
    verifyEmailSubtitle:
      "We've sent a secure 6-digit verification code to your email address.",
    verifyEmailChange: "Change",
    verifyEmailCodeSent: "Code Sent",
    verifyEmailAccessGranted: "Access Granted",
    verifyEmailSecureChannel: "Secure Channel Established",
    verifyEmailValidating: "Validating...",
    verifyEmailVerify: "Verify Email",
    verifyEmailDidntReceive: "Didn't receive the code?",
    verifyEmailResendIn: "Resend in {{seconds}}",
    verifyEmailResending: "Transmitting...",
    verifyEmailSendNewCode: "Send New Code",
    verifyEmailSecurityTerms: "Security Terms",
    verifyEmailEnterEmail:
      "Enter your email address to receive and verify your code.",
    verifyEmailEnterCode: "Enter the verification code sent to your email.",
    verifyEmailCompleteCode: "Please complete the 6-digit verification code.",
    verifyEmailSuccess:
      "Identity verified successfully. Redirecting to dashboard...",
    verifyEmailLinkSuccess:
      "Your email has been verified. Establishing secure connection...",
    verifyEmailLinkError: "Verification failed. The link may have expired.",
    verifyEmailInvalidPacket:
      "Verification failed. Invalid authentication packet.",
    verifyEmailResendSuccess:
      "A secure verification packet has been re-transmitted.",
    verifyEmailResendFailed: "Unable to resend. Please try again later.",
  },
  dashboard: {
    liveMonitoring: "Live Monitoring",
    monitoringTitle: "LIVE MONITORING",
    secureNodeActive: "Secure Node 01 • Active",
    camera: "Camera",
    provisioning: "PROVISIONING...",
    criticalAlert: "Critical Alert",
    detectLabel: "DETECTED",
    captureIncident: "Capture Incident",
    drawingMode: "Drawing Mode",
    inCameraAnnotation: "In-Camera Annotation",
    // TEMPORARY v2.1 FIRST-TERM RESTRICTION: remove these messages when
    // restoring the RESTRICTED panel for the second-term release.
    comingSoon: {
      title: "Coming Soon",
      description:
        "We're working on this feature and plan to make it available in a future update.",
    },
    drawingInstructions: {
      restricted: "Restricted zone: draw a polygon and double-click to finish.",
      direction:
        "Direction line: create an arrow line and double-click to save.",
      tripwire: "Tripwire: draw a line and double-click to finalize.",
      initial: "Click to place points. Double click to finish polygon.",
      saved: "Drawing saved.",
      cleared: "Drawing cleared.",
      removed: "Last point removed.",
      saving: "Saving zone...",
      saveFailed: "Failed to save zone.",
      restrictedMinPoints: "Restricted Area requires at least 3 points.",
    },
    tripwire: {
      configureTitle: "Configure Tripwire",
      confirmTitle: "Confirm Current Occupancy",
      confirmDescription:
        "This tripwire needs a fresh occupancy confirmation after system restart.",
      name: "TRIPWIRE name",
      namePlaceholder: "e.g. Main Entrance",
      allowedGroupSize: "Maximum allowed group size",
      currentOccupancy: "Current people inside",
      entryDirection: "Entry direction (toward D)",
      directionLeft: "Entry moves toward D on the left",
      directionRight: "Entry moves toward D on the right",
      remaining: "Remaining",
      inside: "Inside",
      overLimit: "Over limit",
      confirm: "Confirm occupancy",
      invalidConfiguration:
        "Enter a name, positive group size, non-negative occupancy, and select a direction.",
      confirmationFailed: "Unable to confirm tripwire occupancy.",
      confirmationPending: "Occupancy confirmation pending",
      silenceAlarm: "Silence alarm",
      alarmSilenced: "Alarm silenced",
    },
    controls: {
      pause: "Pause",
      play: "Play",
      enterDrawing: "Enter Drawing Mode",
      toggleFullscreen: "Toggle fullscreen",
      cameraStrip: "Camera Strip",
      awaitingLink: "Awaiting Encrypted Link",
      doubleClickHint:
        "Double click to finish • Right click to undo • ESC to cancel",
      rightClickHint: "Right click to undo",
      escHint: "ESC to cancel",
      snapshot: "Capture Snapshot",
      muteCamera: "Mute audio for {{camera}}",
      unmuteCamera: "Unmute audio for {{camera}}",
    },
    cameraButton: "Camera",
    status: {
      running: "Running",
      offline: "Offline",
      processing: "Processing",
    },
    alerts: {
      critical: "Critical Alerts",
      generic: "Alerts",
      sources: "Sources",
    },
    savedZones: "Saved Zones",
    alertBadgeDefault: "Alert",
    alertBadgeRestricted: "Restricted Area",
    cameraStatusLive: "LIVE FEED",
    cameraStatusDisconnected: "DISCONNECTED",
    cameraStatusUnknown: "UNKNOWN",
    engineAlt: "AeroGuard Engine",
  },
  cameras: {
    title: "Infrastructure Nodes",
    subtitle: "Manage live RTSP streams and historical video archives",
    addButton: "Add Infrastructure",
    types: {
      live: "Live RTSP/IP",
      upload: "Video Archive",
      usb: "Laptop Camera",
    },
    modalTitle: "Register New Node",
    cameraAliasPlaceholder: "Node Alias (e.g. Gate 04)",
    locationPlaceholder: "Physical Location",
    streamPlaceholder: "rtsp://admin:password@ip:port",
    invalidStreamFormat:
      "Invalid RTSP URL. Enter the RTSP stream URL provided by your camera or NVR. Example: rtsp://username:password@192.168.1.100:554/stream",
    liveProvisionFailed:
      "Unable to connect to the RTSP camera. Check the camera address and network connection.",
    liveProvisionProbeFailed:
      "The RTSP camera could not be opened or did not provide a video frame.",
    uploadLabel: "Select Video File",
    cameraUsedMessage: "Laptop Camera will be used",
    cameraUsedDetail: "OpenCV will connect to Camera 0 automatically.",
    provisionButton: "PROVISION NODE",
    aiActive: "AI Active",
    deleteCamera: "Delete Camera",
    confirmDeleteCamera: "Delete this camera and all related data?",
    deleteSuccess: "✅ Camera deleted successfully!",
    deleteFailed: "❌ Failed to delete camera. Try again.",
    provisionSuccess: "✅ Node Provisioned Successfully!",
    provisionFailed: "❌ Failed to add camera. Check connection.",
    provisionPartial: "Camera created, but AI initialization failed.",
    initializeAi: "Initialize AI Node",
    cameraBadge: "Camera Type",
    liveIcon: "LIVE",
    uploadIcon: "UPLOAD",
    usbIcon: "USB",
    cameraSingular: "Camera",
    cameraPlural: "Cameras",
    status: {
      liveFeed: "LIVE FEED",
      disconnected: "DISCONNECTED",
      pending: "PENDING",
    },
    modalDescription:
      "Select the type of node you want to add and provide the required details.",
    starting: "Starting...",
    deletingNode: "Deleting Node...",
    provisioning: "Provisioning Node...",
    rtspAccessibilityHint:
      "Make sure your RTSP stream is accessible and the URL is correct.",
    videoFile: "Video File",
    uploadDropPrompt: "Drag & Drop your video file here",
    uploadBrowsePrompt: "or click to browse",
    uploadFormats: "Supported formats: MP4, MOV, AVI, MKV • Max size: 2GB",
    laptopCameraInfoTitle: "Laptop Camera Information Panel",
    defaultCamera: "Default Camera (0)",
    cameraReady: "Camera is ready and connected",
    cameraAutoConnect: "OpenCV will connect to Camera 0 automatically.",
    aiInitFailed: "Failed to initialize AI node.",
    operationFailed: "Operation Failed",
    uploadFileRequired: "Please select a video file.",
  },
  analytics: {
    pageTitle: "System Intelligence Analytics",
    pageSubtitle: "Real-time AI Detection Statistics",
    allCameras: "All Cameras",
    noDataTitle: "No Analytics Data",
    noDataSubtitle:
      "No detections found for the selected date range and camera.",
    errorTitle: "Failed to Load Analytics",
    errorSubtitle:
      "The dashboard API request failed. Please verify backend service and try again.",
    chartTitles: {
      timeline: "Detection Timeline",
      distribution: "Threat Distribution",
      frequency: "Detection Frequency Over Time",
      severity: "Severity Distribution",
      topCameras: "Top Cameras",
      recentAlerts: "Recent Alerts",
      heatmap: "Detection Heatmap (Hourly Density)",
    },
    tableHeaders: {
      camera: "Camera",
      location: "Location",
      detections: "Detections",
      status: "Status",
    },
    kpis: {
      totalDetections: "Total Detections",
      criticalAlerts: "Critical Alerts",
      highAlerts: "High Alerts",
      mediumAlerts: "Medium Alerts",
      lowAlerts: "Low Alerts",
      weapons: "Weapons",
      fire: "Fire",
      persons: "Persons",
      vehicles: "Vehicles",
      averageConfidence: "Average Confidence",
      activeCameras: "Active Cameras",
      aiAccuracy: "AI Accuracy",
      suspiciousObjects: "Suspicious Objects",
    },
    liveDataset: "Live dataset",
    poweredBy:
      "Dashboard is powered by /api/v1/reports/dashboard via reportService.",
    severity: {
      critical: "Critical",
      high: "High",
      medium: "Medium",
      low: "Low",
      normal: "Normal",
    },
    categories: {
      person: "Person",
      baggage: "Baggage",
      fire: "Fire",
      vehicle: "Vehicle",
      suspiciousObject: "Suspicious Object",
    },
    kpiTrends: {
      totalWindow: "{{count}} detections in the selected window",
      criticalDatabase: "{{count}} critical alerts from the database",
      highSeverity: "{{count}} high-severity detections",
      mediumSeverity: "{{count}} medium-severity detections",
      lowSeverity: "{{count}} low-severity detections",
      suspiciousObjects: "{{count}} unknown or suspicious objects",
      fireDetections: "{{count}} fire or smoke detections",
      personDetections: "{{count}} person detections",
      vehicleDetections: "{{count}} vehicle detections",
      averageConfidence: "{{value}}% average confidence from detections",
      activeCameras: "{{count}} connected cameras for {{cameraName}}",
    },
    alertDescriptions: {
      abandonedBag: "Abandoned bag detected",
      loitering: "Loitering detected",
      restrictedArea: "Restricted area detected",
      unknown: "Unknown event type",
    },
    alertInvestigation: {
      searchByAlertId: "Search by Alert ID",
      eventIdPlaceholder: "Enter the Event ID from the Alert PDF.",
      loadingMatches: "Loading matches...",
      noMatchingAlertIds: "No matching Alert IDs found.",
      enterEventId: "Please enter an Event ID.",
      invalidEventId: "Please enter a valid Event ID.",
      alertNotFound: "Alert not found",
      noAlertMatches: "No alert matches this Event ID.",
      signInRequired: "Please sign in to continue.",
      unauthorized: "You are not authorized to view this alert.",
      noAlertSelected: "No alert selected.",
      loadingAlertDetails: "Loading alert details...",
      clear: "Clear",
      severity: "Severity",
      confidence: "Confidence",
      camera: "Camera",
      location: "Location",
      detectedAt: "Detected At",
      evidence: "Evidence",
      alertEvidenceAlt: "Alert evidence",
      loadingEvidence: "Loading evidence...",
      evidenceUnavailable: "Evidence image unavailable.",
      technicalReference: "Technical Reference",
      eventId: "Event ID",
      copyId: "Copy ID",
    },
    viewAllDevices: "View All Devices",
    noSeverityChart: "No severity chart available.",
    heatmapTooltip: "{{count}} detections",
    alertsLabel: "Alerts",
  },
  profile: {
    title: "Security Profile",
    subtitle: "Clearance Level",
    accountStatus: "Account Status",
    systemId: "System ID",
    accessHistory: "Node Access History",
    commissionedOn: "Commissioned On",
    lastLogin: "Last System Login",
    registryData: "Registry Data",
    discardChanges: "Discard Changes",
    unknownDevice: "Unknown device",
    global: "Global",
    logoutAll: "Logout all",
    logoutAllDescription: "Are you sure you want to logout all sessions?",
    modifyRecord: "Modify Record",
    fullIdentityName: "Full Identity Name",
    corporateEmail: "Corporate Email",
    secureContactLine: "Secure Contact Line",
    assignedOrganization: "Assigned Organization",
    commitUpdate: "Commit Update",
    credentialRotation: "Credential Rotation",
    currentSystemPassword: "Current System Password",
    newSecurePassword: "New Secure Password",
    confirmNewPassword: "Confirm New Password",
    rotateCredentials: "Rotate Credentials",
    personnelDirectory: "Personnel Directory",
    personnelDirectorySubtitle:
      "Authorized to manage all system nodes and operator access records",
    avatarAlt: "Profile avatar",
    changeEmail: "Change",
    changeEmailPrompt: "Enter your new email:",
    online: "Online",
    defaultName: "System administrator",
    defaultRole: "admin",
    defaultSystemId: "CCFF-096B",
    viewLogs: "View logs",
    initialInstantiation: "Initial instantiation completed by system root.",
    lastLoginDescription: "Neural-link handshake verified at node-04.",
    activeSessions: "Active sessions",
    sessionId: "Session ID",
    loginDateTime: "Login date & time",
    deviceType: "Device type",
    active: "Active",
    idle: "Idle",
    noActiveSessions: "No active sessions found.",
    privacyPolicy: "Privacy Policy",
    termsOfService: "Terms of Service",
    documentation: "Documentation",
    support: "Support",
    contact: "Contact",
    copyright: "© 2027 AeroGuard AI. All rights reserved.",
    registryNotice:
      "Registry modifications require secondary biometric verification and administrative approval.",
    passwordPlaceholder: "••••••••••••",
    passwordHint: "Min. 32 characters",
    passwordReenter: "Re-enter password",
  },
  privacyPolicy: {
    pageTitle: "Privacy Policy | AeroGuard AI",
    eyebrow: "AeroGuard AI",
    title: "Privacy Policy",
    lastUpdatedLabel: "Last Updated:",
    lastUpdated: "August 23, 2026",
    intro:
      "AeroGuard AI is an intelligent video surveillance platform designed to help organizations monitor cameras, detect security events, and respond to potential incidents. This Privacy Policy explains what information may be processed when you use the platform, how that information is used, and how it is protected.",
    glanceTitle: "Privacy at a Glance",
    sectionNavigation: "Policy sections",
    contactButton: "Contact Support",
    glance: {
      0: {
        title: "Access Controlled",
        text: "Only authorized users can access protected resources.",
      },
      1: {
        title: "Camera Data",
        text: "Camera streams are processed for security monitoring.",
      },
      2: {
        title: "AI-Assisted Detection",
        text: "AI supports security analysis and event detection.",
      },
      3: {
        title: "Event Records",
        text: "Security events may be stored for monitoring and investigation.",
      },
    },
    sections: {
      overview: {
        title: "{{index}}. Overview",
        p1: "AeroGuard AI is designed to assist organizations with intelligent video surveillance, security monitoring, event detection, and incident awareness.",
        p2: "This Privacy Policy explains the categories of information that may be processed by the platform, how that information is used, how access is controlled, and how users can obtain information about the handling of their data. The exact information processed may depend on the features enabled and the deployment environment in which AeroGuard AI is operated.",
      },
      information: {
        title: "{{index}}. Information We Collect",
        p1: "Depending on the enabled features and deployment, AeroGuard AI may process the following categories of information:",
        p2: "Account and technical information is used to provide the application and protect its resources.",
        item1:
          "Account information: name or username, email address, account information, and role or permissions where used.",
        item2:
          "Camera configuration data: camera name, location, IP address where configured, RTSP URL where configured, camera type, status, and camera-specific annotation configurations.",
        item3:
          "Security and detection data: detection type, severity, camera identifier, timestamp, tracking or event information, alert state, and event evidence or screenshots where generated.",
        item4:
          "Technical information: session or authentication state, application status information, and operational logs where applicable.",
      },
      camera: {
        title: "{{index}}. Camera & Video Data",
        p1: "AeroGuard processes video streams from cameras configured by authorized users. Video frames may be processed by the computer vision pipeline to detect people, objects, security conditions, and other configured events.",
        p2: "Depending on the event and system configuration, selected frames or screenshots associated with security events may be stored as evidence. AeroGuard does not represent that entire camera streams are permanently stored.",
        item1: "People and object detection",
        item2: "Fire, flame, and smoke detection",
        item3: "Restricted Area, direction, and tripwire events",
        item4: "Loitering and unattended or abandoned object events",
      },
      ai: {
        title: "{{index}}. AI & Analytics",
        p1: "AeroGuard uses computer vision and AI-assisted processing to analyze camera frames and generate operational results.",
        p2: "AI-generated detections and classifications are intended to assist security monitoring and should not be treated as guaranteed, error-free identification or decision-making.",
        item1: "Object detection and person tracking",
        item2: "Security-event and severity classification",
        item3: "Ownership relationships for unattended objects",
        item4:
          "Persistent person display identifiers within the system's processing context",
      },
      use: {
        title: "{{index}}. How We Use Information",
        p1: "Information may be used to operate and improve the security-monitoring workflow provided by the deployment.",
        p2: "AeroGuard does not use the information described here for advertising or ad personalization as part of its core surveillance workflow.",
        item1: "Operate user accounts and manage configured cameras",
        item2:
          "Process video streams, detect security events, and generate alerts",
        item3:
          "Maintain event history and display dashboards, analytics, and reports",
        item4:
          "Maintain system reliability, diagnose operational issues, and protect the platform against unauthorized use",
      },
      account: {
        title: "{{index}}. Account & Authentication",
        p1: "AeroGuard uses account authentication, user roles, authorization checks, protected resources, and account or session state to control access to the application.",
        p2: "Where the application provides a 'Remember this device' option, enabling it may cause a session or device token to be stored in the browser to maintain authentication for the configured period. The exact behavior depends on the deployment configuration.",
      },
      security: {
        title: "{{index}}. Data Storage & Security",
        p1: "AeroGuard applies technical, application-level, and access-control measures intended to protect stored information and limit access to authorized users.",
        p2: "These measures may include authenticated API access, role-based authorization, database access controls, server-side validation, and restricted access to camera and event resources. The security of a deployment also depends on its infrastructure, network configuration, credentials, and operational policies.",
      },
      retention: {
        title: "{{index}}. Data Retention",
        p1: "Security events and related records may remain stored for as long as they are required for operational monitoring, investigation, reporting, or system administration.",
        p2: "Retention periods may depend on the deployment configuration, database policies, administrator settings, storage capacity, and organizational requirements. AeroGuard does not state a fixed retention period unless one is configured by the deployment.",
      },
      sharing: {
        title: "{{index}}. Data Sharing",
        p1: "AeroGuard does not require unrelated third-party access to camera streams for the core surveillance workflow.",
        p2: "Depending on the deployment environment, information may be processed by infrastructure or service providers used to operate, host, store, or maintain the application. Access to protected data should be limited according to the deployment's authentication, authorization, and administrative controls.",
      },
      rights: {
        title: "{{index}}. User Rights",
        p1: "Depending on the deployment and applicable policies, users may be able to request information about the handling of their data through the AeroGuard administrator or official support channel.",
        p2: "The available process and scope of any request depend on the organization operating the deployment and applicable administrative policies.",
        item1: "Access account information",
        item2: "Update account information",
        item3:
          "Request clarification about data processing or correction of inaccurate account information",
        item4:
          "Request deletion where supported by the deployment and applicable administrative policies",
      },
      cookies: {
        title: "{{index}}. Cookies & Local Storage",
        p1: "The AeroGuard web application may use browser cookies, local storage, session storage, or similar browser mechanisms to support authentication, user preferences, language settings, and core application functionality.",
        p2: "The exact mechanisms used may depend on the application configuration and deployment environment. AeroGuard does not introduce advertising or tracking storage as part of the core application workflow.",
      },
      thirdParty: {
        title: "{{index}}. Third-Party Services",
        p1: "AeroGuard AI may be deployed using third-party infrastructure, hosting, database, storage, authentication, or other operational services.",
        p2: "The specific services involved depend on the deployment environment selected by the organization operating the platform. Users should refer to their deployment or organization administrator for information about specific infrastructure providers where required.",
      },
      changes: {
        title: "{{index}}. Changes to This Policy",
        p1: "We may update this Privacy Policy when the platform's features, data processing practices, security controls, or deployment model change.",
        p2: "When material changes are made, the 'Last Updated' date at the top of this page will be updated accordingly.",
      },
      contact: {
        title: "{{index}}. Contact",
        p1: "Questions about privacy or data handling?",
        p2: "For privacy-related questions, account concerns, or data-handling requests, contact the AeroGuard administrator or the official support channel provided by your deployment.",
      },
    },
  },
  termsOfServicePage: {
    pageTitle: "Terms of Service | AeroGuard AI",
    eyebrow: "AeroGuard AI",
    title: "Terms of Service",
    lastUpdatedLabel: "Last Updated:",
    lastUpdated: "August 23, 2026",
    intro:
      "These Terms of Service govern access to and use of AeroGuard AI. By accessing or using the platform, users agree to use the system responsibly, comply with applicable policies and laws, and follow the responsibilities described in these terms.",
    glanceTitle: "Terms at a Glance",
    sectionNavigation: "Terms sections",
    contactButton: "Contact Support",
    glance: {
      0: {
        title: "Authorized Use",
        text: "Use AeroGuard only with appropriate permission and authority.",
      },
      1: {
        title: "Account Responsibility",
        text: "Protect account credentials and use assigned permissions appropriately.",
      },
      2: {
        title: "Camera Responsibility",
        text: "Only configure cameras and streams you are authorized to access.",
      },
      3: {
        title: "AI-Assisted Monitoring",
        text: "AI detections and alerts assist human operators and may contain inaccuracies.",
      },
    },
    sections: {
      acceptance: {
        title: "{{index}}. Acceptance of Terms",
        p1: "These Terms of Service govern access to and use of AeroGuard AI. By accessing or using the platform, you acknowledge that you have read and understood these terms and agree to use the service in accordance with them and with applicable policies and laws.",
        p2: "If you do not agree with these terms, you should not use the platform. These terms describe product use responsibilities and are not a substitute for legal advice.",
      },
      service: {
        title: "{{index}}. Description of the Service",
        p1: "AeroGuard AI is an intelligent video surveillance platform designed to assist organizations with camera management, live RTSP/IP camera monitoring, video stream processing, AI-assisted object and person detection, security-event detection, annotations and security zones, alerts and notifications, event records and evidence, reports, operational monitoring, and user roles and permissions where enabled.",
        p2: "AeroGuard is intended to assist security monitoring and situational awareness. It does not guarantee prevention or detection of every security event.",
      },
      eligibility: {
        title: "{{index}}. Eligibility and User Accounts",
        p1: "Users should have appropriate authorization to use the deployment and are responsible for information they provide to the platform. Users must protect their account credentials, avoid sharing accounts where prohibited by their deployment, and remain responsible for actions performed under their credentials.",
        p2: "Assigned roles and permissions should be used appropriately. Access and functionality can differ based on configured roles such as Administrator, Supervisor, or Officer.",
      },
      acceptableUse: {
        title: "{{index}}. Acceptable Use",
        p1: "Users may use AeroGuard to monitor authorized cameras, configure legitimate camera sources, create legitimate annotations and monitoring rules, review security events, manage alerts and reports, and support legitimate security, monitoring, operational, or organizational purposes.",
        p2: "Users must not use AeroGuard for unauthorized access, unlawful monitoring, credential misuse, security bypasses, disruption, malicious uploads, attacks on other systems, deceptive manipulation of alerts or event records, or other unlawful activity.",
        item1:
          "Access cameras without authorization or monitor individuals without appropriate legal or organizational authority.",
        item2:
          "Use stolen or unauthorized camera credentials, or bypass authentication or authorization controls.",
        item3:
          "Intentionally overload, disrupt, or interfere with platform security.",
        item4:
          "Upload malicious software or harmful content, or use the platform to attack other systems or networks.",
        item5:
          "Intentionally manipulate alerts or event records for deception or misuse the platform for unlawful activity.",
      },
      cameraResponsibilities: {
        title: "{{index}}. Camera and Data Responsibilities",
        p1: "Users who configure a camera are responsible for having authorization to access it and permission to monitor the location and subjects it captures. They are also responsible for ensuring that the configured RTSP/IP source is legitimate, camera credentials are valid and protected, and network configuration permits the connection.",
        p2: "Users are responsible for determining whether their camera deployment and monitoring activities are permitted under applicable laws, regulations, contracts, and organizational policies. AeroGuard does not determine whether a user's camera deployment is legally authorized.",
      },
      aiAlerts: {
        title: "{{index}}. AI Detection and Alerts",
        p1: "AeroGuard uses AI and computer vision to assist with detection and monitoring of people, objects, Fire, Flame, Smoke, Restricted Area, Direction, Tripwire, Loitering, and unattended or abandoned objects.",
        p2: "AI-generated detections, classifications, tracking results, ownership associations, and alerts may contain false positives, false negatives, tracking errors, or other inaccuracies. Users should review important events before taking consequential actions. AI-assisted output is not a guaranteed fact or substitute for human judgment.",
      },
      securityCredentials: {
        title: "{{index}}. Security and Credentials",
        p1: "Users are responsible for maintaining the confidentiality of credentials associated with their accounts and configured camera sources. Credentials should not be shared unnecessarily, and should be updated when compromise is suspected.",
        p2: "Users should use appropriate permissions and report suspicious access through the official channel provided by their deployment. AeroGuard cannot prevent every credential compromise.",
      },
      userContent: {
        title: "{{index}}. User Content and Evidence",
        p1: "Users may configure camera metadata, annotations, monitoring rules, security-event records, and evidence or screenshots generated by the platform.",
        p2: "Users remain responsible for ensuring they have the necessary rights and authority to use the data they provide or cause the system to process. Event screenshots and evidence are generated for operational or security purposes and may depend on system configuration; not all video or frames are retained permanently.",
      },
      externalCameras: {
        title: "{{index}}. External Cameras and Third-Party Dependencies",
        p1: "Live RTSP/IP operation can depend on physical camera hardware, NVRs, network connectivity, RTSP/RTSPS availability, camera credentials, camera configuration, firewall or router configuration, and the hosting or infrastructure environment.",
        p2: "A camera may become unavailable because of network failures, configuration changes, incorrect credentials, power loss, firewall restrictions, or third-party infrastructure issues. AeroGuard cannot guarantee availability of external camera hardware or networks outside the application's control.",
      },
      availability: {
        title: "{{index}}. Service Availability and Technical Limitations",
        p1: "AeroGuard does not guarantee continuous uptime, uninterrupted camera streaming, uninterrupted AI processing, perfect detection, zero latency, zero system errors, or continuous network connectivity.",
        p2: "Interruptions may result from maintenance, hardware failure, RTSP source failure, network outages, infrastructure issues, resource limitations, browser or device issues, or software bugs. No service-level or uptime commitment is created by these terms.",
      },
      intellectualProperty: {
        title: "{{index}}. Intellectual Property",
        p1: "AeroGuard software, interface, branding, design, and associated materials may be protected by applicable intellectual-property rights. Users receive permission to use the platform according to the deployment and applicable authorization.",
        p2: "Users should not copy, resell, redistribute, reverse-engineer, or misuse the platform except where permitted by applicable law or explicit authorization. These terms do not identify a particular legal owner or entity beyond the deployment context.",
      },
      suspension: {
        title: "{{index}}. Suspension and Termination",
        p1: "AeroGuard administrators or deployment operators may restrict, suspend, or terminate access according to the policies governing the deployment.",
        p2: "This may be appropriate in response to misuse, unauthorized access attempts, violation of these terms, intentional disruption, security threats, or administrative or deployment decisions. No elaborate enforcement process is implied.",
      },
      disclaimers: {
        title: "{{index}}. Disclaimers",
        p1: "AeroGuard AI is provided as a security-monitoring and decision-support tool. It does not guarantee detection of every incident, prevention of every security event, uninterrupted operation, or perfect camera connectivity.",
        p2: "The platform does not guarantee complete accuracy of AI detections, person or object tracking, or ownership associations, and does not guarantee the absence of false positives or false negatives. Users remain responsible for reviewing important events and applying appropriate human judgment.",
      },
      liability: {
        title: "{{index}}. Limitation of Liability",
        p1: "To the extent permitted by applicable law, AeroGuard and its deployment operators are not responsible for losses caused by camera hardware failures, third-party network outages, incorrect RTSP configuration, unauthorized user actions, misuse of the platform, AI detection errors, missed or false alerts, infrastructure outages, or failures outside the reasonable control of the platform or deployment operator.",
        p2: "This deployment-aware product wording is not a complete legally enforceable limitation and should be reviewed with appropriate legal counsel for the relevant deployment. No jurisdiction or monetary liability cap is specified here.",
      },
      changes: {
        title: "{{index}}. Changes to These Terms",
        p1: "We may update these Terms of Service when the platform's capabilities, policies, security practices, or deployment model change.",
        p2: "When material changes are made, the 'Last Updated' date will be updated accordingly. Users should review the current version periodically.",
      },
      contact: {
        title: "{{index}}. Contact",
        p1: "Questions about these Terms?",
        p2: "For questions about platform use, access, responsibilities, or deployment-specific policies, contact the AeroGuard administrator or the official support channel provided by your deployment. Do not rely on this page as formal legal advice.",
      },
    },
  },
  documentation: {
    pageTitle: "Documentation | AeroGuard AI",
    eyebrow: "AeroGuard AI",
    title: "Documentation",
    intro:
      "Learn how to configure, monitor, and operate AeroGuard AI, from account access and camera setup to AI-assisted detection, security rules, alerts, and event monitoring.",
    heroCallout:
      "AeroGuard is an operator-facing video surveillance platform. Start with the quick guide, then choose an article from the navigation when you need a focused explanation.",
    getStarted: "Get Started",
    cameraSetup: "Camera Setup",
    searchLabel: "Search documentation",
    searchPlaceholder: "Search documentation...",
    clearSearch: "Clear search",
    noResults: "No matching articles found.",
    noResultsHint: "Try camera, RTSP, alerts, tripwire, bag, or AI.",
    navigation: "Documentation navigation",
    previous: "Previous",
    next: "Next",
    groups: {
      gettingStarted: "Getting Started",
      cameras: "Camera Management",
      dashboard: "Dashboard",
      ai: "AI & Detection",
      rules: "Security Rules",
      annotations: "Annotations",
      alerts: "Alerts & Events",
      users: "Users & Access",
      troubleshooting: "Troubleshooting",
      reference: "Reference",
    },
    articles: {
      introduction: {
        title: "Introduction",
        summary:
          "AeroGuard helps authorized operators monitor cameras, analyze video, configure rules, and respond to security events.",
        body: "The basic flow is Camera -> Video stream -> AI processing -> Detection and tracking -> Security rules -> Events -> Notifications or alarms. A camera supplies frames, the processor analyzes supported objects and conditions, rules add context, and the application presents results for an operator to review.\nUse the sidebar to learn one task at a time. Behavior can depend on camera configuration, enabled settings, network conditions, and the deployment.",
      },
      login: {
        title: "Login & Authentication",
        summary:
          "Sign in with the account credentials provided for your deployment.",
        body: "Open the application and enter your username and password, then submit the login form. A successful login takes you to the authenticated application shell. Failed credentials are shown as an error and do not open protected pages.\nThe deployment uses account/session state to protect resources. Password reset is not documented here because no reset workflow was found in the current frontend. The Remember this device behavior is deployment-dependent and should only be described when that option is present in the running build.",
      },
      quickStart: {
        title: "Quick Start",
        summary: "A short first session for a new operator.",
        body: "1. Sign in.\n2. Open Cameras and choose LIVE RTSP/IP, Video Archive, or Laptop Camera.\n3. Add the source and wait for the result of validation or upload.\n4. Select a camera and open Dashboard.\n5. Start monitoring, confirm the status and video view, and review overlays.\n6. If required, select the camera, configure an annotation or security rule, and save it.\n7. Review notifications and event evidence when an event is produced. If a camera stays offline, use Camera Offline and RTSP Problems in Troubleshooting.",
      },
      roles: {
        title: "Roles & Permissions",
        summary:
          "Access is determined by the deployment role and camera ownership.",
        body: "New registration defaults to the Officer role. The repository defines roles as named records, but the explicit global administrator checks use the exact name Administrator. Administrators can manage users and generally receive global access; other roles are normally limited to resources owned by the current user.\nCameras, events, and reports use owner-scoped access for non-administrators. User listing, creation, and deletion are restricted to Administrator. There is no separate Supervisor permission policy verified in the current authorization code, so a Supervisor role should not be assumed to have a special capability. A missing feature may therefore reflect role scope rather than a broken button.",
      },
      cameraOverview: {
        title: "Camera Overview",
        summary:
          "The Cameras page is where sources are registered, selected, and managed.",
        body: "Camera records include a name or alias, location, source type, stream URL where applicable, status, and ownership information. The available source choices are LIVE RTSP/IP, Video Archive upload, and Laptop Camera/USB. The list is filtered by ownership for non-administrators.\nUse the camera list to select a source, inspect its status, and open the dashboard workflow. If a source is missing, confirm that you are using the authorized account that owns it or an Administrator account.",
      },
      liveRtsp: {
        title: "Add LIVE RTSP/IP Camera",
        summary:
          "Register a network camera or NVR stream by validating its URL and first frame.",
        body: "Open Cameras -> Register New Node -> LIVE RTSP/IP. Enter the Node Alias, Physical Location, and the RTSP URL, then choose Provision Node.\nExample only:\nrtsp://username:password@192.168.1.100:554/stream\nUse the URL supplied by the camera or NVR. The username, password, IP address, port, and path above are placeholders and may differ. The server accepts rtsp:// or rtsps:// URLs with a network location, probes the stream with OpenCV, reads a real frame, and only then saves the camera.\nInvalid format, an unreachable source, incorrect credentials, a timeout, or no frame produces an inline provisioning error under the RTSP field. A live camera is initially represented as Offline until analysis is started.",
      },
      videoArchive: {
        title: "Video Archive",
        summary:
          "Upload a supported video file for archive-based processing instead of a live RTSP source.",
        body: "Choose Video Archive in the camera registration flow and select a video file. The backend accepts mp4, mov, avi, mkv, and webm extensions and stores the upload under the deployment's video upload directory with a generated name.\nThe backend limit is 200 MiB, even though the current UI contains a stale 2GB helper label. Archive records are not provisioned by probing an RTSP URL. If the upload is rejected, check its extension and size, then review the returned error.",
      },
      laptopCamera: {
        title: "Laptop Camera",
        summary:
          "Use the computer's default camera through the USB source option.",
        body: "Choose Laptop Camera or USB when registering a source. The application stores the source as 0, which the processor maps to the default OpenCV camera and CAP_DSHOW on Windows.\nAllow camera access in the browser and operating system when prompted. The camera must be connected and available to the machine running the processor. To stop using it, stop the camera analysis or remove the source according to your deployment controls. Permission denial, a busy camera, or a missing device can leave the source unavailable.",
      },
      cameraStatus: {
        title: "Camera Status",
        summary:
          "Status tells you whether the source is being processed or has stopped.",
        body: "The dashboard displays Running, Offline, and Processing based on camera and websocket state. Processing means startup or analysis work is in progress; Running means the dashboard has received the active AI status; Offline means analysis has stopped or the source is unavailable.\nThe Cameras page also exposes backend status values such as Online, Processing, and Offline. Labels are not perfectly aligned across all views, so use the dashboard state and stream view together when diagnosing a source.",
      },
      cameraSelection: {
        title: "Camera Selection",
        summary:
          "Choose the camera whose stream, overlays, rules, and events you are reviewing.",
        body: "Selecting a camera stops the previous dashboard session and starts the selected one. The selected source controls the stream and the camera-local event context. An annotation created for Camera A does not automatically apply to Camera B.\nIf an overlay or rule seems absent, confirm the selected camera and the selected annotation type before editing or saving.",
      },
      dashboard: {
        title: "Dashboard Overview",
        summary:
          "The Dashboard combines camera monitoring, overlays, controls, and notifications.",
        body: "Use the camera selector to choose a source, inspect the current status, and monitor the live view. The dashboard can show AI bounding boxes and labels, person or ownership identifiers, security overlays, notification access, screenshot actions, start/stop controls, fullscreen, and annotation controls when the relevant state is available.\nControls can be affected by camera status and role ownership. Start with the selected camera and confirm that it is Running before expecting live detections.",
      },
      liveView: {
        title: "Live Camera View",
        summary:
          "Read the stream, detection boxes, labels, identities, and security state together.",
        body: "A running view can show bounding boxes around supported detections, labels such as person, baggage, fire, smoke, or flame, and rule labels such as RESTRICTED AREA, WRONG DIRECTION, or TRIPWIRE. Red/DANGER indicates a critical security condition in the processor path; yellow/WARNING indicates a warning condition such as loitering.\nPerson display IDs are continuity aids within a camera session, not guaranteed facial identities. If the view is blank or stale, check the camera status, source connectivity, and the stream troubleshooting articles.",
      },
      cameraControls: {
        title: "Camera Controls",
        summary:
          "Use the controls that are visible for the selected dashboard state.",
        body: "Start begins analysis for the selected camera when it is not running. Stop ends the active analysis and returns the source toward Offline. Screenshot captures the current view when the dashboard provides that action. Notification controls open the event history and related actions. Annotation controls switch between editing modes and draft operations.\nA control may be unavailable while a camera is processing, when no camera is selected, or when the current role cannot access the resource. Treat the visible state as authoritative rather than assuming every control is available everywhere.",
      },
      fullscreen: {
        title: "Fullscreen View",
        summary:
          "Expand the monitoring view when you need a larger inspection area.",
        body: "Use the fullscreen control shown with the dashboard camera view. It expands the current monitoring surface using the browser's available viewport; exit with the browser or view control provided by the running interface.\nFullscreen does not change camera ownership, rules, or AI processing. If the control is absent, confirm that a camera view is active and that the browser permits fullscreen requests.",
      },
      aiDetection: {
        title: "AI Detection",
        summary:
          "The processor analyzes frames using supported model classes and configurable modules.",
        body: "The current processor keeps person, baggage-related classes, vehicles, fire, smoke, and flame detections and discards unsupported model classes. Confidence expresses how strongly the model supports a detection; it is not a guarantee that the result is correct. Person confidence uses a lower recall-oriented threshold bounded between 0.25 and 0.5.\nDetection records are throttled per camera, track, and type, so one visible object does not necessarily create a database record on every frame. Use AI output as monitoring assistance and review important events yourself.",
      },
      fireSmoke: {
        title: "Fire / Flame / Smoke",
        summary:
          "Fire, flame, and smoke are handled as critical alarm sources when their modules are enabled.",
        body: "Fire and flame use the fire_detection_enabled setting; smoke uses smoke_detection_enabled. Enabled detections are labeled in uppercase, shown as DANGER with red boxes, added to alarm sources, and sent through the critical alert path.\nThe dashboard plays the fire alarm audio for fire, flame, or smoke when sounds are enabled. Confirm the source and the evidence before taking consequential action; the AI result is not a guarantee of an actual fire.",
      },
      personTracking: {
        title: "Person Tracking",
        summary:
          "Tracking links observations of a person across nearby frames on one camera.",
        body: "The processor keeps track positions and movement state per camera so it can maintain continuity and evaluate rules such as loitering or direction. A track can disappear because of occlusion, missed frames, or source conditions.\nTracking is operational context, not a permanent identity. Alert creation is throttled, so a continuing condition may not create a new event every frame.",
      },
      personIds: {
        title: "Persistent Person IDs",
        summary:
          "Displayed IDs provide short-lived continuity within the application's camera processing context.",
        body: "The interface may show a label such as ID:006 Person. The identity registry is appearance-based, camera-local, and session-only. It can preserve an ID through temporary track loss when histogram similarity exceeds 0.92, and identities expire after 60 seconds; a cleared registry starts again from 1.\nThese IDs are not database identities, guaranteed facial recognition, or cross-camera global identities. Treat them as a practical display and tracking aid.",
      },
      ownership: {
        title: "Object Ownership",
        summary:
          "A nearby person can be associated with a baggage object for camera-local monitoring.",
        body: "Ownership is assigned using the nearest person within the configured distance and normally requires three consecutive matching frames. An overlay can therefore show Person ID:006 and Bag A -> Owned ID 006.\nTemporary owner loss can preserve the association for the configured missing-frame count. After that, the bag can become temporarily unattended and later unattended, which changes its security state. Ownership is camera-local and can be affected by occlusion, distance, and tracking quality.",
      },
      abandonedBags: {
        title: "Abandoned Bags",
        summary:
          "A bag must remain continuously unattended for 60 seconds before confirmation.",
        body: "A nearby person is associated with a bag using the existing camera-local ownership rules. After owner loss is confirmed, the bag remains in a pending state for 60 continuous seconds; an owner return resets that timer. At 60 seconds the bag turns red, an ABANDONED_BAG critical event and alarm are activated once, and a screenshot is captured immediately. Further screenshots are attached to the same event every five seconds until the event ends. The configured abandoned_bag_seconds value is normalized to 60 seconds.",
      },
      restrictedArea: {
        title: "Restricted Area",
        summary:
          "A polygon rule detects when a bounding box intersects a configured restricted zone.",
        body: "Select Restricted Area, choose Add Region, click at least three boundary points, finish the polygon, review it, and Save. The rule is camera-specific and requires restricted_area_enabled. When a supported object's box intersects the polygon, the processor labels it RESTRICTED AREA, marks it DANGER/red, and sends a critical alert through the common path.\nIf it does not trigger, confirm the selected camera, saved points, module setting, object position, and that the camera is processing.",
      },
      wrongDirection: {
        title: "Wrong Direction",
        summary:
          "A Direction line evaluates movement relative to its configured orientation.",
        body: "Select Direction, choose Add Region, place exactly two endpoints, finish the line, and Save. The processor evaluates side crossing and the movement vector relative to the configured line; a negative dot-product crossing is labeled WRONG DIRECTION, marked DANGER, and emits a Critical AI event. A separate legacy vertical heuristic is also gated by wrong_direction_enabled.\nThe inspected processor alarm-source path does not add a dedicated wrong-direction sound source. Do not assume a sound; review the visual event and current alert behavior.",
      },
      tripwire: {
        title: "Tripwire",
        summary:
          "A tripwire is a two-point line that detects an object's side crossing.",
        body: "Select Tripwire, choose Add Region, place exactly two endpoints, finish, and Save. A side crossing marks the object DANGER, labels it TRIPWIRE, and emits one Critical event per object and zone within the five-second alert cooldown.\nIf the line is not effective, verify that it belongs to the selected camera and type, that it was saved, and that the object actually crosses the line while processing is active.",
      },
      loitering: {
        title: "Loitering",
        summary:
          "Loitering identifies a person who remains near the same position for the configured time.",
        body: "When loitering is enabled, the processor tracks a person's position. Movement greater than 20 pixels resets the movement timestamp; remaining near the same position until loitering_seconds is reached marks the person WARNING/High.\nLoitering is a warning condition in the inspected implementation, not a Critical alarm. If it is absent, check the setting, the selected camera, the configured duration, and whether the person has moved enough to reset the timer.",
      },
      annotationModes: {
        title: "Annotation Modes",
        summary:
          "The editor has separate modes for Restricted Area, Direction, and Tripwire.",
        body: "Choose the mode before drawing. Restricted Area uses a polygon with at least three points. Direction and Tripwire use lines with exactly two points. Switching modes changes what the editor is creating; points from one type do not become another type.\nThe draft is associated with the current camera. Select the correct source before changing a saved rule.",
      },
      addRegion: {
        title: "Add Region",
        summary:
          "Add Region starts a draft shape for the selected annotation mode.",
        body: "Select the desired mode first, then choose Add Region. Click the points on the camera view, finish the drawing, and review the draft. Restricted Area needs three or more points; Direction and Tripwire need two. The completed shape remains a local draft until Save is used.\nIf the shape is wrong, use Undo or Escape according to the editor state, then redraw it.",
      },
      undo: {
        title: "Undo",
        summary:
          "Undo reverses the most recent supported draft or deletion action.",
        body: "The current editor records drawing history. Undo can remove the last point or draft action and can recreate a deleted persisted zone through the backend add-zone operation. Backspace or right-click also invokes the editor's undo behavior; Enter finishes a drawing and Escape exits and discards drafts.\nIf a change has already been saved and is not in the editor history, select the correct camera and type, then use the supported delete and save workflow rather than assuming browser undo will restore it.",
      },
      delete: {
        title: "Delete",
        summary:
          "Delete removes a saved region for the current camera and annotation type.",
        body: "Use Delete while editing the selected camera and mode. For a persisted zone, the dashboard calls the backend immediately and records the action for undo. The saved zone is removed from the current editor state; use Save to reconcile the current mode's remaining draft with persisted data.\nDeletion is camera-specific. Confirm the selected camera and mode before removing a region.",
      },
      save: {
        title: "Save",
        summary:
          "Save reconciles additions and deletions for the currently selected drawing mode.",
        body: "Save compares the current draft with persisted zones for the selected camera and mode. Missing persisted zones are deleted and draft zones are created. The backend stores normalized points with source dimensions and returns normalized zone data.\nSave one annotation type at a time. After saving, refresh or reselect the camera if the view does not immediately show the updated overlays. Other cameras and other annotation types are not automatically changed.",
      },
      cameraZones: {
        title: "Camera-Specific Zones",
        summary:
          "Saved annotations belong to both a camera and an annotation type.",
        body: "Camera A can have Restricted Area A1 while Camera B has Restricted Area B1. Camera B does not automatically use Camera A's zones. Direction and Tripwire regions are also separate types.\nWhen a rule appears missing, select the camera that owns it, choose the matching mode, and confirm that the region was saved.",
      },
      alertLevels: {
        title: "Alert Levels",
        summary: "Severity communicates how the processor classified an event.",
        body: "Persisted standard detections default to Medium. In the common detection path, DANGER maps to Critical and WARNING maps to High. The AI event path also stores explicit severities such as Critical or High.\nThe separate decision engine contains additional mappings, but the inspected processor path does not visibly invoke it. Use the severity shown on the actual notification or event rather than inferring a level from an object label.",
      },
      notifications: {
        title: "Notification Center",
        summary:
          "The notification center collects AI events and provides event actions.",
        body: "The application loads AI events, falls back to the notifications endpoint when needed, resolves camera names from camera metadata, and listens for ai_event websocket messages. A notification can show event type, camera, severity, timestamp, and available evidence.\nUse Read or mark-all-read actions as available, View to inspect an event, and Download when protected evidence is available. Clear behavior is local to the notification UI; do not assume that clearing changes the server record.",
      },
      eventDetails: {
        title: "Event Details",
        summary:
          "Event details provide the operational context needed to review an alert.",
        body: "Depending on the event, details can include an event ID, camera, detection type, severity, timestamp, confidence, and evidence reference. Camera names are resolved from camera metadata when available.\nReview the camera and timestamp alongside the image or detection context. Missing evidence does not mean that every frame was stored; evidence depends on event and system configuration.",
      },
      evidence: {
        title: "Evidence & Screenshots",
        summary:
          "Selected security events may include a screenshot that can be viewed or downloaded.",
        body: "When an event has protected evidence, use View to open it or Download to save it through the authenticated AI endpoint. The notification UI supports screenshot viewing and download for available event evidence.\nNot every event has an image. If evidence is unavailable, review the event fields, camera stream, and deployment configuration instead of assuming a capture failed.",
      },
      alarmSounds: {
        title: "Alarm Sounds",
        summary:
          "Sound mapping depends on the alarm source and the global sound setting.",
        body: "When sounds are enabled, fire, flame, and smoke sources use the fire alarm audio. Other alarm sources use the security alarm audio. The authenticated application keeps one loop per required sound category while any unmuted camera alarm remains active; both categories may play together.\nUse the camera-strip mute control to silence only that camera. Its mute clears when its alarm resolves. Warning-only conditions such as loitering, and the inspected wrong-direction path, should not be documented as guaranteed sound sources. Browser audio permission and the user sound setting can also prevent playback.",
      },
      settings: {
        title: "User Settings",
        summary:
          "Settings controls are user-scoped and affect processing modules and session behavior.",
        body: "The Settings page loads or creates user-scoped settings and supports partial updates and reset to defaults. Current controls include sound enablement, reconnect, JWT expiration, tracking, face recognition, GPU, frame skip, loitering, crowd density, abandoned bag, wrong direction, restricted area, fire, and smoke.\nThe crowd-density setting is persisted and displayed, but no corresponding processing branch was found in the inspected processor. Only rely on settings that visibly affect the current deployment and check your role if a settings control is unavailable.",
      },
      cameraOffline: {
        title: "Camera Offline",
        summary:
          "An offline source needs a source, network, credential, and status check.",
        body: "Check the RTSP URL, camera or NVR power, network connectivity, credentials, camera configuration, firewall, and application status. For a live source, provisioning must pass URL validation and a real first-frame probe. Then start analysis and watch for Processing followed by Running.\nIf the source stops later, inspect the dashboard websocket status and the camera's external network before changing rules.",
      },
      rtspProblems: {
        title: "RTSP Problems",
        summary:
          "Most RTSP failures occur before registration or while the external source is unreachable.",
        body: "Use the format supplied by the camera or NVR, for example:\nrtsp://username:password@192.168.1.100:554/stream\nConfirm the scheme is rtsp or rtsps, the host and port are reachable, credentials are correct, and the path is valid. Provisioning probes the stream and reads a frame, so a syntactically valid but unavailable URL still fails with an inline error. Check firewall/router rules and the camera/NVR independently.",
      },
      noAlerts: {
        title: "No Alerts",
        summary:
          "An alert requires active processing, an enabled condition, and a matching object or rule.",
        body: "Confirm that the selected camera is Running, the relevant AI or rule setting is enabled, and a saved rule exists for that same camera. Verify that the object actually satisfies the polygon, line, direction, loitering, ownership, or abandoned-bag condition.\nThen inspect notifications and event cooldown behavior. A continuing condition can be throttled, and a model detection can be missed or classified differently.",
      },
      noSound: {
        title: "No Sound",
        summary:
          "Sound requires an active alarm source, enabled sound, and browser playback permission.",
        body: "Check the sound setting, browser audio permissions, the alarm source, and whether the event is warning-only. Fire, flame, and smoke map to the fire alarm; other active sources map to the security alarm. Loitering is WARNING/High and should not be treated as a guaranteed alarm.\nUse the camera-strip mute control to silence only that camera; it clears when the alarm resolves. Audio for other active, unmuted cameras continues.",
      },
      annotationProblems: {
        title: "Annotation Problems",
        summary:
          "Most editor issues come from the selected camera, mode, points, or an unsaved draft.",
        body: "Confirm the selected camera and annotation type. Use at least three points for Restricted Area and exactly two for Direction or Tripwire. Finish the drawing, then Save. Use Undo for the last draft or deletion, and remember that Escape discards drafts.\nIf another camera does not show the zone, that is expected: annotations are camera-specific. If a saved zone remains wrong, delete it in the correct mode and save the reconciled state.",
      },
      faq: {
        title: "FAQ",
        summary: "Answers to common operator questions.",
        body: "What is RTSP? It is the stream address supplied by a network camera or NVR; AeroGuard validates it and reads a first frame during live provisioning.\nWhy did a bag turn yellow or red? Ownership was temporarily lost or the configured unattended conditions were reached; review the camera-local owner state and event.\nWhy does Wrong Direction not play a sound? The inspected explicit direction path creates a Critical event but does not add a dedicated alarm source.\nWhy are zones missing on another camera? Zones are saved per camera and annotation type.\nWhy is a notification still visible after refresh? The app reloads event history from its event/notification endpoints; clearing the local UI does not necessarily delete a server event.",
      },
      systemOverview: {
        title: "System Overview",
        summary:
          "Use this reference chain to understand how a security event reaches an operator.",
        body: "Camera source -> Stream -> AI processing -> Tracking -> Persistent display identity or ownership -> Security rules -> Event -> Notification or alarm.\nThe source provides frames. Processing detects supported classes. Tracking links nearby observations. The identity registry provides short-lived camera-local IDs and ownership associates baggage with a nearby person. Rules evaluate zones, lines, movement, or time. The resulting event is persisted or broadcast, then the dashboard presents a notification, evidence, and an alarm source when applicable.",
      },
    },
  },
  support: {
    pageTitle: "Support Center | AeroGuard AI",
    eyebrow: "AeroGuard AI",
    title: "Support Center",
    intro:
      "Find practical troubleshooting guides for cameras, AI detection, annotations, alerts, and account access. When self-service is not enough, contact the official support channel.",
    searchLabel: "Search support",
    searchPlaceholder: "Search support...",
    clearSearch: "Clear support search",
    noResults: "No support articles found.",
    noResultsHint:
      "Try camera, RTSP, alerts, sound, bag, annotation, or login.",
    contactButton: "Contact Support",
    quickHelp: "Quick Help",
    navigation: "Support navigation",
    previous: "Previous",
    next: "Next",
    emailSupport: "Email Support",
    contactTitle: "Contact Support",
    contactText:
      "If the troubleshooting guides do not resolve the problem, contact the official AeroGuard support channel:",
    securityWarning:
      "Never send passwords, RTSP passwords, API keys, authentication tokens, or private credentials. Remove secrets from screenshots before sending them.",
    groups: {
      center: "Support Center",
      account: "Account & Access",
      cameras: "Cameras",
      ai: "AI & Detection",
      alerts: "Alerts & Notifications",
      annotations: "Annotations",
      general: "General",
    },
    articles: {
      overview: {
        title: "Support Overview",
        summary:
          "Start here for practical help with common AeroGuard workflows.",
        body: "AeroGuard support covers camera registration and status, LIVE RTSP/IP connectivity, AI detection, person IDs, object ownership, abandoned bags, alerts, sounds, annotations, login, permissions, and browser behavior.\nChoose a topic from the navigation or search the complete support catalog. If you contact support, include the exact visible error, camera name and type, approximate time, affected feature, steps already tried, and a redacted screenshot.\nExpected result: support can reproduce or narrow the issue. Contact support when the source, account, or deployment requires administrator access or the documented checks do not resolve the problem.",
      },
      beforeContacting: {
        title: "Before Contacting Support",
        summary:
          "Prepare useful, non-sensitive details so the issue can be diagnosed faster.",
        body: "What you see: support may otherwise have only a general description and cannot identify the failing camera or event.\nCheck and include: exact error text, screenshot with secrets removed, camera name and type, approximate time, affected feature, steps that caused the issue, and browser or device information when relevant.\nSolution: describe what changed and what you already tried, then use Report a Problem with the subject AeroGuard Support Request. Expected result: the support team receives actionable context. Contact support when the issue persists after the relevant guide or needs administrator/deployment action.",
      },
      loginProblems: {
        title: "Login Problems",
        summary:
          "Resolve failed sign-in without guessing at an unavailable password-reset flow.",
        body: "What you see: the login form shows an error and protected pages do not open. Likely causes include incorrect credentials, an unavailable account, or a network/API problem.\nCheck: re-enter the username and password carefully, confirm the application is connected to the deployment, and verify the account with the administrator. Retry once. The current frontend does not expose a password-reset workflow.\nExpected result: valid credentials open the authenticated application shell. Contact the administrator or support with the visible error and approximate time; never send a password or token.",
      },
      permissionProblems: {
        title: "Permission Problems",
        summary:
          "A missing feature or resource may be caused by role or ownership scope.",
        body: "What you see: a camera, event, report, or user action is unavailable or not listed. Non-administrator access is generally scoped to resources owned by the current user; user listing, creation, and deletion are restricted to Administrator.\nCheck your assigned role and whether you own the camera or resource. Ask the system administrator to confirm authorization rather than trying to bypass access controls.\nExpected result: an authorized resource becomes available after the correct account or administrator action. Contact support when the administrator confirms access should exist but the resource remains missing, and include the account identifier and resource name without credentials.",
      },
      sessionProblems: {
        title: "Session Problems",
        summary:
          "Account/session state can prevent access even when the page itself loads.",
        body: "What you see: a protected request fails, you return to login, or the session no longer behaves as expected. Likely causes include session expiration, a revoked session, stale browser state, or a deployment authentication issue.\nCheck: sign in again, refresh the application, confirm the account is active, and retry the same action. Do not copy or send browser tokens. If the issue affects only one browser, compare with a supported modern browser without sharing private data.\nExpected result: a fresh valid session restores authorized access. Contact the administrator or support if repeated sign-in fails and provide the visible error, browser, time, and affected resource.",
      },
      browserProblems: {
        title: "Browser Problems",
        summary:
          "Use safe browser checks for permissions, audio, layout, and stale application state.",
        body: "What you see: controls do not respond, audio is blocked, Laptop Camera is unavailable, or the layout looks incomplete.\nCheck: refresh the application, use a supported modern browser, review site camera and audio permissions, verify the tab is not muted, and test the same workflow after removing only relevant site state if appropriate. Keep the application URL and account private.\nExpected result: the browser permits the required interaction and the interface reloads normally. Contact support with browser name/version, device, screenshot, and exact feature if the issue persists.",
      },
      cameraOffline: {
        title: "Camera Offline",
        summary:
          "Check the source, network, credentials, provisioning result, and processing status.",
        body: "What you see: the camera is Offline, unavailable, or stops after setup. Likely causes include a powered-off camera/NVR, unavailable RTSP source, incorrect credentials, network or firewall issues, invalid configuration, no video frame, or a processing failure.\nCheck: camera power, network connectivity, RTSP URL, credentials, camera/NVR configuration, firewall/router, and the AeroGuard status. For a live source, retry Provision Node so URL validation and first-frame verification run again, then start analysis and watch for Processing followed by Running.\nExpected result: the source passes verification and the dashboard becomes Running. Contact support with camera name/type, status, exact error, time, and redacted configuration when external checks pass.",
      },
      rtspProblems: {
        title: "RTSP Connection Problems",
        summary:
          "Troubleshoot URL format, reachability, credentials, opening, frames, and timeouts.",
        body: "What you see: an inline RTSP error, provisioning failure, timeout, unavailable stream, or a camera that remains Offline. Use this example only: rtsp://username:password@192.168.1.100:554/stream. The username and password are placeholders; use the URL supplied by the camera or NVR.\nCheck: the scheme is rtsp:// or rtsps://, host, port, path, credentials, camera power, network, and firewall/router. A valid-looking URL can still fail if the stream cannot open or no frame arrives.\nSolution: correct the source outside the app, return to LIVE RTSP/IP, enter the corrected URL, and retry provisioning. Expected result: the server opens the stream and reads a first frame. Contact support with the redacted URL shape and exact error, never the password.",
      },
      provisioning: {
        title: "Camera Provisioning Failure",
        summary:
          "Live provisioning validates the URL and confirms a real frame before registration.",
        body: "What you see: the camera is not registered and a persistent message appears below the RTSP field. The flow is Validate URL -> attempt connection -> confirm stream opens -> confirm first frame -> register/start camera.\nCheck: URL syntax, reachable host/port, credentials, camera/NVR availability, and whether a frame is produced. An HTTP 400 may distinguish invalid format, unable to connect, stream open failure, no frame, or timeout depending on the backend response.\nSolution: fix the external source or URL and choose Provision Node again. Expected result: successful verification creates the camera. Contact support with the exact inline message and time when a redacted, independently verified source still fails.",
      },
      streamProblems: {
        title: "Stream Problems",
        summary:
          "Black, empty, frozen, or stopping video usually needs an external-source check.",
        body: "What you see: a black or empty view, a frozen stream, unavailable video, or a camera that becomes Offline.\nCheck: selected camera, camera/NVR power, network, RTSP configuration and credentials, firewall/router, external source availability, and AeroGuard status. Confirm the camera is Running before troubleshooting detections.\nSolution: restore the external source or correct configuration, then retry provisioning for a live camera or restart processing from the dashboard. Expected result: frames appear and status progresses from Processing to Running. Contact support with camera type, status, time, and a screenshot if the source works elsewhere but not in AeroGuard.",
      },
      cameraStatus: {
        title: "Camera Status",
        summary:
          "Interpret Online, Processing, Running, and Offline without treating them as identical labels.",
        body: "What you see: the Cameras page and Dashboard can show different user-facing status labels. Dashboard states include Processing during startup, Running after active AI status, and Offline after stop or source failure. The backend and Cameras page also use Online for newly created upload or USB sources.\nCheck the dashboard status and stream together. Start analysis when appropriate and wait for Processing to become Running; inspect the external source when it becomes Offline.\nExpected result: status matches the actual processing state. Contact support with the page, exact status, camera type, and time if the labels conflict or remain unchanged.",
      },
      noDetection: {
        title: "No AI Detection",
        summary:
          "Confirm processing, enabled modules, visibility, and camera-specific rules.",
        body: "What you see: no person, object, fire, flame, smoke, or rule result appears.\nCheck: the camera is Running, the relevant detection setting is enabled, the object is visible, lighting and framing are usable, and the condition actually matches. For Restricted Area, Direction, or Tripwire, confirm a saved annotation exists for the current camera and type. Check notification/event history after waiting for processing.\nExpected result: a supported detection or event appears when the condition is met. Contact support with camera name/type, enabled feature, approximate time, and screenshot if the source is Running and the condition is reproducible.",
      },
      incorrectDetection: {
        title: "Incorrect AI Detection",
        summary:
          "False positives, false negatives, tracking errors, and classification errors are possible.",
        body: "What you see: a detection is missing, incorrectly labeled, appears at low confidence, or a rule state does not match what you expect.\nCheck camera quality, lighting, object visibility, confidence/settings where available, active rules, and annotations. Review whether the supported class and condition actually match the scene. AI output assists monitoring and is not guaranteed to be correct.\nExpected result: configuration and scene limitations are understood, though no setting guarantees perfect accuracy. Contact support with a redacted screenshot, camera type, time, visible label/confidence, and the reproducible conditions.",
      },
      personIds: {
        title: "Person ID Issues",
        summary:
          "Displayed person IDs are short-lived, camera-local continuity aids.",
        body: "What you see: an ID changes, a person disappears and reappears with another ID, or two people appear difficult to distinguish. The internal tracker ID and displayed appearance-based identity are separate concepts.\nCheck whether the person remained continuously visible, whether occlusion or missed frames occurred, and whether the camera/session changed. Refreshing the stream can restart processing context; observe whether the identity stabilizes without expecting cross-camera identity.\nExpected result: IDs provide useful local continuity, not guaranteed facial recognition. Contact support with camera, time, visible IDs, and a redacted screenshot if reproducible with clear visibility.",
      },
      ownership: {
        title: "Object Ownership Issues",
        summary:
          "Bag ownership is camera-local and can change with distance, visibility, and tracking.",
        body: "What you see: a bag has the wrong owner, no owner, or multiple bags appear associated with one person. Ownership uses the nearest person within configured distance and normally needs three consecutive matching frames. Temporary owner loss can preserve the association for configured missing frames.\nCheck the camera view, person visibility, distance, occlusion, selected camera, and whether the association persists across frames. Multiple bags can be associated with the same person when the matching conditions support it.\nExpected result: ownership reflects the current camera-local tracking context, not a permanent identity guarantee. Contact support with camera, time, object/person labels, and screenshot if the scene is clear and the association remains wrong.",
      },
      abandonedBags: {
        title: "Abandoned Bag Issues",
        summary:
          "A pending bag turns red only after 60 continuous unattended seconds.",
        body: "What you see: an owned bag is green, a pending unattended bag is yellow, and a confirmed abandoned bag is red with an active event.\nCheck that the person was actually associated and the camera is Running. The timer starts when owner loss is confirmed, resets if the owner returns, and requires 60 continuous unattended seconds. Confirmation activates one ABANDONED_BAG critical event and alarm, captures a screenshot immediately, then captures another every five seconds while the event remains active.\nExpected result: a returning owner cancels the pending timer; a later owner loss starts a fresh 60-second interval. Contact support with camera, time, visible owner label, state progression, and event details.",
      },
      noAlerts: {
        title: "No Alerts",
        summary:
          "An alert needs active processing, an enabled condition, and a matching object or rule.",
        body: "What you see: an expected notification or event is absent.\nCheck the camera is Running, the relevant feature is enabled, the correct camera is selected, the required annotation is saved for that camera and type, and the object actually satisfies the rule. Check event history and notification state. A continuing condition can be subject to cooldown and AI detections can be missed or classified differently.\nExpected result: a matching condition creates the relevant event and notification when processing and configuration allow it. Contact support with camera, rule/feature, time, status, and a screenshot when the condition is reproducible.",
      },
      notificationProblems: {
        title: "Notification Problems",
        summary:
          "Review live websocket events, loaded history, read state, and evidence availability.",
        body: "What you see: a notification is missing, appears after refresh, lacks details, or View/Download is unavailable. The app loads AI events, falls back to notifications, resolves camera names, and listens for ai_event websocket messages.\nCheck camera status, event time, notification bell state, read/unread state, and whether the event has evidence. Use View or Download only when those actions are available. Clearing the local notification UI does not necessarily delete the server event.\nExpected result: available events reappear from history after refresh; unavailable evidence remains unavailable. Contact support with event type, camera, severity, timestamp, and visible UI state, without tokens.",
      },
      eventHistory: {
        title: "Event History",
        summary:
          "Historical events and live notifications use different paths but share event context.",
        body: "What you see: a live event, a persisted event after refresh, read/unread state, or a missing event image. The notification service loads event history and merges event IDs; live ai_event websocket messages add current events.\nCheck the event camera, severity, timestamp, read state, and refresh once. View or Download depends on protected evidence being available. Do not assume clearing the UI removes the stored event.\nExpected result: persisted history can reload when the deployment endpoint returns it. Contact support with the event ID or timestamp, camera, and action that failed when a reproducible event is absent.",
      },
      alarmSoundProblems: {
        title: "No Alarm Sound",
        summary:
          "Sound requires the setting, browser playback, and an alarm source that actually maps to audio.",
        body: "What you see: no sound or a sound different from what you expected.\nCheck the alert sound setting, browser audio permissions, site/tab mute state, camera processing, and event type. Fire, flame, and smoke map to the fire alarm; other active alarm sources map to the security alarm. Warning-only conditions such as loitering do not guarantee sound, and the inspected explicit Wrong Direction path does not add a dedicated sound source. Check whether that camera is muted in the Dashboard camera strip; its mute clears when the alarm resolves.\nExpected result: an active mapped alarm plays when sound is enabled and the browser permits it. Contact support with event type, source, setting state, browser, and time.",
      },
      fireSmoke: {
        title: "Fire / Flame / Smoke Alerts",
        summary:
          "These detections are module-controlled critical alarm sources.",
        body: "What you see: uppercase fire, flame, or smoke label, a red DANGER box, a critical event, and potentially fire alarm audio. Fire and flame require fire_detection_enabled; smoke requires smoke_detection_enabled.\nCheck the relevant setting, Running camera, visible scene, event history, evidence availability, and browser sound permission. Do not treat an absent screenshot as proof that no event occurred; evidence depends on configuration.\nExpected result: an enabled supported condition enters the critical path and can create an event and alarm source. Contact support with the camera, enabled module, timestamp, visible label, and event details when the condition is clear and reproducible.",
      },
      annotationProblems: {
        title: "Annotation Problems",
        summary:
          "Check camera, mode, point count, draft state, and Save/Delete/Undo behavior.",
        body: "What you see: a zone is not visible, points appear in the wrong mode, Save did not persist, or another camera does not contain the zone.\nCheck: select the correct camera and type. Restricted Area needs at least three points; Direction and Tripwire need exactly two. Use Add Region, finish the drawing, then Save. Undo removes the last supported draft/deletion action; Delete immediately removes a persisted zone and Save reconciles the selected mode. Escape discards drafts.\nExpected result: the saved zone appears only for its camera and annotation type. Contact support with camera, mode, point count, save/delete action, and screenshot if a reproducible saved state is wrong.",
      },
      commonIssues: {
        title: "Common Issues",
        summary:
          "A compact first check for the most frequent support requests.",
        body: "Camera Offline: check network, power, RTSP configuration, credentials, and status.\nNo Detection: check Running state, feature settings, object visibility, and camera-specific rules.\nNo Sound: check audio permissions, sound setting, and event type.\nZone Missing: check selected camera, annotation type, point count, and Save.\nRTSP Invalid or No Frame: check URL format and camera/NVR stream availability.\nNo Notification: check event conditions, cooldown, notification state, and history. Expected result: the relevant focused article provides the next checks. Contact support with exact error and affected resource when those checks fail.",
      },
      faq: {
        title: "Frequently Asked Questions",
        summary: "Quick answers for common AeroGuard support questions.",
        body: "How do I contact support? Use Email Support or Report a Problem to open a message to Eslam.Adel2596@gmail.com with subject AeroGuard Support Request.\nHow do I add LIVE RTSP/IP? Use Cameras -> Register New Node -> LIVE RTSP/IP, enter the camera/NVR URL, and Provision Node.\nWhy is a camera Offline? Check source power, network, URL, credentials, firewall, and processing status.\nWhy are there no detections or alerts? Confirm Running state, enabled feature, visible condition, selected camera, and saved camera-specific rule.\nWhy does Wrong Direction not play an alarm? The inspected direction path creates a Critical event but does not add a dedicated alarm source.\nWhy did the bag turn yellow or red? Ownership was lost or configured unattended conditions completed; timing is deployment-configured.\nWhy are annotations absent on another camera? Zones are camera- and type-specific.\nWhat should I include in a report? Exact error, camera/type, time, affected feature, steps tried, browser/device, and redacted screenshot. Never include secrets.",
      },
    },
  },
  contactPage: {
    pageTitle: "Contact Us | AeroGuard AI",
    eyebrow: "AeroGuard AI",
    title: "Contact Us",
    intro:
      "Have a question, want to learn more about AeroGuard AI, or need to get in touch with the project team? Choose the contact method that works best for you.",
    visitSupport: "Visit Support",
    primaryEyebrow: "Direct Contact",
    primaryTitle: "Get in Touch",
    emailAeroGuard: "Email AeroGuard",
    call: "Call",
    secondaryEyebrow: "Stay Connected",
    secondaryTitle: "More Ways to Connect",
    sendEmail: "Send Email",
    methodsTitle: "Contact Methods",
    methods: {
      email: {
        title: "Email",
        description:
          "For general questions, project inquiries, technical questions, and direct communication.",
        action: "Send Email",
      },
      phone: {
        title: "Phone",
        description:
          "For direct contact regarding AeroGuard AI and project-related inquiries.",
        action: "Call",
      },
      github: {
        title: "GitHub",
        description:
          "Explore the AeroGuard project and related development work.",
        action: "View GitHub",
      },
      linkedin: {
        title: "LinkedIn",
        description:
          "Connect professionally and learn more about the project team.",
        action: "View LinkedIn",
      },
      facebook: {
        title: "Facebook",
        description: "Connect through the official Facebook profile.",
        action: "View Facebook",
      },
    },
    reasonsTitle: "Contact Reasons",
    reasons: {
      general: {
        title: "General Inquiry",
        text: "Questions about AeroGuard AI, its purpose, or its capabilities.",
      },
      technical: {
        title: "Technical Question",
        text: "Questions about configuration, operation, or technical behavior. For operational troubleshooting, visit the Support Center.",
      },
      project: {
        title: "Project Information",
        text: "Questions about the project, technology stack, capabilities, or deployment.",
      },
      collaboration: {
        title: "Collaboration / Professional Contact",
        text: "Professional communication or collaboration-related inquiries.",
      },
    },
    supportTitle: "Need help with an existing problem?",
    supportText:
      "For camera, RTSP, AI, alert, notification, annotation, or account issues, visit the AeroGuard Support Center.",
    supportButton: "Visit Support Center",
    securityTitle: "Security Notice",
    securityText:
      "Never include passwords, RTSP passwords, API keys, authentication tokens, private credentials, or other secrets in contact messages. Remove sensitive information from screenshots first.",
    faqTitle: "Contact FAQ",
    faq: {
      howContact: {
        question: "How can I contact AeroGuard?",
        answer:
          "Email Eslam.Adel2596@gmail.com or use the official social and contact links on this page.",
      },
      technicalHelp: {
        question: "How can I get technical help?",
        answer:
          "Visit the Support Center for operational troubleshooting guides.",
      },
      github: {
        question: "Can I contact AeroGuard through GitHub?",
        answer: "Yes. The official GitHub link is available on this page.",
      },
      linkedinFacebook: {
        question: "Can I contact AeroGuard through LinkedIn or Facebook?",
        answer: "Yes. The official profiles are provided on this page.",
      },
      call: {
        question: "Can I call directly?",
        answer:
          "Yes. The official contact phone number is +201093397961. No response-time guarantee is implied.",
      },
    },
    summaryTitle: "Official Contact Information",
    labels: { email: "Email", phone: "Phone" },
  },
  settings: {
    title: "System Settings",
    subtitle: "Core Intelligence & Infrastructure Parameters",
    loadDefaults: "Load Defaults",
    saveDeploy: "SAVE & DEPLOY",
    environment: "Environment",
    airportName: "Airport Name",
    airportNamePlaceholder: "e.g. Dubai International (DXB)",
    timeZone: "Time Zone",
    aiCore: "AI Core",
    objectConfidenceThreshold: "Object Confidence Threshold",
    faceRecognition: "Person Recognition",
    motionTracking: "Motion Tracking",
    notificationEngine: "Notification Engine",
    dashboardAudioSiren: "Dashboard Audio Siren",
    securityLifecycle: "Security Lifecycle",
    sessionExpiration: "Session Expiration (Minutes)",
    factoryDefaultsConfirm:
      "Restore factory defaults? Current changes will be lost.",
    saveSuccess: "✅ System configuration deployed successfully!",
    saveFailed:
      "❌ Critical Error: Could not sync settings with the AI Engine.",
    factoryDefaultsTitle: "Load Defaults",
    activeDeployment: "Active deployment - 14.2ms latency verified",
    connected: "Connected",
    notificationEngineDescription: "Triggers audible alarm on security breach",
    securityLifecyclePersistent: "Persistent Operation",
    securityLifecyclePersistentDescription:
      "System remains active indefinitely",
    securityLifecycleAutoShutdown: "Auto Shutdown",
    securityLifecycleAutoShutdownDescription:
      "The system will automatically stop after the specified hours",
    hours: "HRS",
    aiVisionModules: "AI Vision Modules",
    modules: {
      gpuAcceleration: "GPU Acceleration",
      gpuAccelerationDescription:
        "Enable GPU for model inference (if available)",
      frameSkip: "Frame Skip",
      frameSkipDescription: "Skip N frames between inferences to save CPU",
      loiteringDetection: "Loitering Detection",
      loiteringDetectionDescription: "Detects persons loitering in an area",
      crowdDensity: "Crowd Density",
      crowdDensityDescription: "Counts people and alerts on threshold",
      abandonedBag: "Abandoned Bag Detection",
      abandonedBagDescription: "Detects ownerless bags",
      wrongDirection: "Wrong Direction",
      wrongDirectionDescription:
        "Alerts when people move against allowed direction",
      restrictedArea: "Restricted Area",
      restrictedAreaDescription: "Named polygon zones with intrusion alerts",
      fireDetection: "Fire Detection",
      fireDetectionDescription: "Integrate pretrained fire model",
      smokeDetection: "Smoke Detection",
      smokeDetectionDescription: "Integrate pretrained smoke model",
    },
  },
  reports: {
    pageTitle: "Analytics Reports",
    pageSubtitle: "Unified view of detections and violations",
    managerTitle: "Reports Manager",
    titlePlaceholder: "Report title (optional)",
    fetchFailed: "Failed to fetch analytics data.",
    reportTypeCustom: "Custom",
    reportTypeSummary: "Summary",
    reportTypeCompliance: "Compliance",
    allCameras: "All Cameras",
    generateReport: "Generate Report",
    searchReports: "Search saved reports",
    history: "History",
    noReports: "No reports yet",
    exportStarted: "Download Started",
    exportStartedDescription: "Your report is being downloaded.",
    deleteTitle: "Delete report?",
    deleteDescription: "Are you sure you want to delete this report?",
    deleteSuccess: "Report deleted successfully.",
    deleteFailed: "Failed to delete report",
    generateMissingDates: "Please select start and end dates",
    generateSuccess: "Report generated: {{id}}",
    generateFailed: "Failed to generate report",
    exportFailed: "Failed to export {{type}}",
  },
  owner: {
    header: "Owner console",
    customerAdministration: "Customer administration",
    navigation: {
      label: "Owner navigation",
      unread: "Unread Requests",
      underReview: "Under Review",
      customers: "Platform Customers",
      logout: "Log out",
      close: "Close owner navigation",
      open: "Open owner navigation",
      collapse: "Collapse owner sidebar",
      expand: "Expand owner sidebar",
      collapseTitle: "Collapse sidebar",
      expandTitle: "Expand sidebar",
    },
    workflow: "Customer workflow",
    sections: {
      unread: {
        title: "Unread Requests",
        description: "Verified customer registrations awaiting initial review.",
      },
      underReview: {
        title: "Under Review",
        description: "Requests being evaluated before platform activation.",
      },
      customers: {
        title: "Platform Customers",
        description: "Active and inactive customers with platform access.",
      },
    },
    search: "Search",
    searchPlaceholder: "Name or phone",
    searchLabel: "Search by name or phone",
    customerCount: "{{count}} customers",
    customerCount_one: "{{count}} customer",
    customerCount_other: "{{count}} customers",
    refresh: "Refresh",
    retry: "Retry",
    loadingCustomers: "Loading customers…",
    loadingCustomer: "Loading customer…",
    noCustomers: "No customers found.",
    customersLoadFailed: "Customers could not be loaded. Please try again.",
    customerLoadFailed: "Customer details could not be loaded. Please try again.",
    emailVerified: "Email verified",
    emailNotVerified: "Email not verified",
    table: {
      customer: "Customer",
      phone: "Phone",
      organization: "Organization",
      registered: "Registered",
      status: "Status",
    },
    status: {
      unread: "Unread",
      underReview: "Under review",
      awaitingEmailVerification: "Awaiting email verification",
      platformCustomer: "Platform customer",
      pending: "Pending",
      active: "Active",
      inactive: "Inactive",
      verified: "Verified",
      notVerified: "Not verified",
    },
    open: "Open",
    previousPage: "Previous page",
    nextPage: "Next page",
    pagination: "{{from}}–{{to}} of {{total}}",
    details: {
      customerWorkflow: "Customer workflow",
      moveToReview: "Move to review",
      activate: "Activate",
      activateAccount: "Activate Account",
      deactivate: "Deactivate",
      reactivate: "Reactivate",
      customerDetails: "Customer details",
      username: "Username",
      email: "Email",
      password: "Password",
      phone: "Phone",
      organization: "Organization",
      registrationDate: "Registration date",
      lastUpdated: "Last updated",
      emailVerification: "Email verification",
      platformConfiguration: "Platform configuration",
      configurationDescription: "Set access and limits before activation.",
      save: "Save",
      saving: "Saving",
      maximumCameraCount: "Maximum Camera Count",
      notConfigured: "Not configured",
      privateOwnerNotes: "Private Owner notes",
      activationRequirement:
        "Activation requires a verified email and a configured maximum camera count.",
    },
    errors: {
      requestFailed: "The request could not be completed. Please try again.",
      maximumCameras:
        "Maximum cameras must be a non-negative whole number.",
      configurationSaveFailed: "Configuration could not be saved.",
      customerUpdateFailed: "The customer could not be updated.",
      profileNotFound: "Customer profile not found.",
      changesSaveFailed: "Unable to save customer changes.",
      moveToReviewFailed: "Request cannot move to review.",
      activationFailed: "Customer cannot be activated.",
      customerNotPending: "Customer is not pending.",
      emailNotVerified: "Customer email is not verified.",
      cameraCountRequired: "Maximum camera count must be configured.",
      cameraCountInvalid: "Maximum camera count is invalid.",
      customerNotActive: "Customer is not active.",
      customerNotInactive: "Customer is not inactive.",
    },
    actions: {
      moveToReview: "Move to review",
      activate: "Activate",
      deactivate: "Deactivate",
      reactivate: "Reactivate",
    },
    confirm: {
      activateTitle: "Activate customer?",
      moveToReviewTitle: "Move request to review?",
      deactivateTitle: "Deactivate customer?",
      reactivateTitle: "Reactivate customer?",
      moveToReview: "Move {{name}} to Under Review?",
      activate: "Activate {{name}}?",
      deactivate: "Deactivate {{name}}?",
      reactivate: "Reactivate {{name}}?",
      confirm: "Confirm",
    },
    success: {
      configurationSaved: "Configuration saved",
      configurationUpdated: "Customer settings were updated.",
      customerUpdated: "Customer updated",
      movedToReview: "Request moved to Under Review.",
      activated: "Customer was activated.",
      deactivated: "Customer was deactivated.",
      reactivated: "Customer was reactivated.",
    },
  },
  alertHistory: {
    title: "Alert History",
  },
};

export default en;
