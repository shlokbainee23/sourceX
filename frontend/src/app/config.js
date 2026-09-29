/**
 * SIH26237 - Configuration & Constants
 * Operational settings for the WESEE / MoD Offline Forensic Workstation
 */

export const SYSTEM_INFO = {
  name: 'SIH26237 Offline Forensic Attribution Workstation',
  authority: 'WESEE — Weapons and Electronics Systems Engineering Establishment',
  organization: 'Ministry of Defence, Government of India',
  securityLevel: 'RESTRICTED DEFENSE ASSET',
  airgapStatus: 'AIR-GAPPED ENVIRONMENT (ZERO EXTERNAL TRAFFIC)',
  pqcStandards: 'FIPS 203 (ML-KEM-768) · FIPS 204 (ML-DSA-44)',
};

export const ROLES = {
  AUTHORITY: 'AUTHORITY',
  RECIPIENT: 'RECIPIENT',
  INVESTIGATOR: 'INVESTIGATOR',
  AUDITOR: 'AUDITOR',
};

export const DEFAULT_STATIONS = [
  {
    principal_id: 'WESEE_HQ',
    role: 'AUTHORITY',
    name: 'WESEE Headquarters (Sender Authority)',
    rank: 'Station Command',
    description: 'Document registration, broadcast encryption authority, key attestation and trust anchor management.',
  },
  {
    principal_id: 'R001',
    role: 'RECIPIENT',
    name: 'Commander Alpha',
    rank: 'Navigation Officer (Naval Command)',
    description: 'Authorized recipient station for strategic fleet directives. Step-up decryption and delivery terminal.',
  },
  {
    principal_id: 'R002',
    role: 'RECIPIENT',
    name: 'Officer Bravo',
    rank: 'Communications Director (Fleet Signals)',
    description: 'Authorized recipient station for naval signal communications and tactical directives.',
  },
  {
    principal_id: 'R003',
    role: 'RECIPIENT',
    name: 'Officer Charlie',
    rank: 'Weapons Specialist (Tactical Systems)',
    description: 'Authorized recipient station for tactical combat and ordinance directives.',
  },
  {
    principal_id: 'INVESTIGATOR_01',
    role: 'INVESTIGATOR',
    name: 'Naval Forensics Investigator',
    rank: 'Forensic Laboratory Specialist',
    description: 'Document intake, 10-point fail-closed cryptographic verification, visual invariance analysis and dossier management.',
  },
  {
    principal_id: 'AUDITOR_01',
    role: 'AUDITOR',
    name: 'Ledger Auditor',
    rank: 'Independent Integrity Inspector',
    description: 'Ledger block verification, cryptographic chain inspection, audit event trail and adversarial tamper testing.',
  },
];

export const ERROR_MAPPINGS = {
  401: {
    title: 'SESSION EXPIRED / AUTHENTICATION REQUIRED',
    message: 'Your cryptographic session has expired or the credentials provided are invalid. Re-authenticate with your keystore passphrase.',
  },
  403: {
    title: 'ACTION NOT AUTHORIZED',
    message: 'Your current role or station identity is not permitted to perform this operation. No state was altered.',
  },
  404: {
    title: 'RESOURCE NOT FOUND',
    message: 'The requested document, session, block, or dossier report does not exist in the database.',
  },
  409: {
    title: 'STATE / PROVENANCE CONFLICT',
    message: 'The operation could not be completed due to a cryptographic state conflict or previous commitment.',
  },
  410: {
    title: 'DELIVERY COPY DESTROYED',
    message: 'The one-time marked delivery copy has already been downloaded and destroyed per security policy. Plaintext cannot be retrieved.',
  },
  422: {
    title: 'INVALID REQUEST DATA',
    message: 'One or more required fields are missing or improperly formatted for this operational endpoint.',
  },
  500: {
    title: 'INTERNAL SYSTEM ERROR',
    message: 'An internal cryptographic or database processing error occurred. The system has failed closed.',
  },
};
