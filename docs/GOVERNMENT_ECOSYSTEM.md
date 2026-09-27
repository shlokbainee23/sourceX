# Government Ecosystem: Research, Decisions and Integration

The research was done on 27 Sep 2026, against official Government of India publications only. The deciding question for each source was: does it materially strengthen an **offline, air-gapped cryptographic provenance system**? If not, it is not integrated.

## Conclusion

> **No external government API is required at runtime.** SIH26237 is an offline cryptographic provenance system. Its core problem is cryptographic and provenance-centric, not data-dependent, so **no government dataset is required for the core system**.

Government sources were used where they genuinely strengthen the system:
- as **design and deployment requirements**: classification vocabulary, key management, logging, time source and PQC migration guidance;
- as **one localized deliverable**: CERT-In-aligned SBOM and CBOM artefacts for supply-chain assurance across the air gap.

The only *authoritative external data* the system needs is the issuing authority's statement of its principals and their keys. That statement enters as a **signed trust manifest**, a signed data package pinned to the authority key. It is the controlled-ingestion path for any future authoritative source.

## Decision matrix

| Source | Purpose | Relevance | Access | Offline fit | Security risk | Decision |
|---|---|---|---|---|---|---|
| CERT-In SBOM/QBOM/CBOM Guidelines v2.0 | Supply-chain transparency, crypto inventory | High | Public PDF | Full (offline generation) | None added | **LOCALIZE**: `scripts/generate_bom.py` → `bom/` |
| Issuing-authority roster and keys (WESEE HQ) | Recipient identity, key attestation, revocation | Core | Internal to the authority | Full (signed package) | Controlled by pin, signature and monotonicity | **INTEGRATE**: signed trust manifest (`app/trust.py`) |
| MHA NISPG (2014) | Classification levels, key-management and logging controls | High | Public PDF | N/A (policy) | None | **REFERENCE**: classification vocabulary already matches; deployment gates documented |
| CERT-In Directions 28 Apr 2022 | Clock sync to NIC/NPL, 180-day log retention | Medium | Public PDF | Via local NTP/GNSS | None | **REFERENCE**: audit trail is append-only; time-source requirement documented |
| CERT-In Guidelines for Govt Entities (2023) | Baseline controls (no unencrypted keys, logging, NTP) | Medium | Public PDF | N/A | None | **REFERENCE**: mapped in SECURITY.md |
| TEC 910018:2025 (PQC migration) | Justifies PQC, crypto inventory, crypto-agility, hybrid | High | Public PDF | N/A | None | **REFERENCE**: CBOM implements the inventory; hybrid gap documented |
| CSIR-NPL IST / UTC(NPLI) NTP | Authoritative national time | Medium | Public NTP | Only via a traceable local time server | Network exposure if called live | **REFERENCE**: deployment requirement, no runtime call |
| CCA / RCAI (India PKI, IT Act) | Legally recognised DSCs, CRL/OCSP, time stamping | Low for PQC prototype | Licensed CAs; online CRL/OCSP | CRLs could be snapshotted | New trust root, classical algorithms | **REFERENCE ONLY** |
| API Setu (MeitY) | Government API marketplace | None found | Organisational onboarding (PAN, GST, authority letter), API keys | Online gateway | Credentials, network dependency | **REJECT** |
| DigiLocker / Entity Locker / Meri Pehchaan | Citizen/entity document issuance and verification | None | Partner onboarding, OAuth, Aadhaar consent | Online only | Personal-data exposure | **REJECT** |
| data.gov.in (OGD, NDSAP) | Public non-sensitive datasets | None | Registration + API key | Snapshot possible | Irrelevant data | **REJECT** |
| DPDP Act 2023 + Rules 2025 | Personal-data obligations for recipient names | Medium (context) | Public law | N/A | N/A | **REFERENCE**: data minimisation documented; no compliance claim |

## Source register

Each entry uses the same fields: source, owner, URL, type, what it provides, why it is relevant, access, online/offline compatibility, security implication, licensing, and decision.

### 1. CERT-In Technical Guidelines on SBOM, QBOM & CBOM, AIBOM and HBOM, v2.0
- **Owner:** CERT-In, MeitY.
- **URL:** https://www.cert-in.org.in/PDF/TechnicalGuidelines-on-SBOM,QBOM&CBOM,AIBOM_and_HBOM_ver2.0.pdf (listed as CISG-2024-02).
- **Type:** Technical guideline.
- **Provides:**
  - SBOM minimum elements: name, version, supplier, licence, dependencies, checksums, timestamp, author, and more;
  - QBOM/CBOM minimum elements for cryptographic assets: asset type, primitive, crypto functions, OID, key/protocol/certificate properties;
  - CycloneDX and SPDX formats;
  - SBOM requirements for software supplied to government.
- **Relevance:** Defence procurement will ask for an SBOM. For a cryptographic system, a CBOM is the auditable statement of which algorithms and keys exist, and that none are quantum-vulnerable.
- **Access:** Public.
- **Online/offline:** Fully offline. The generator reads installed package metadata and code constants.
- **Security implication:** Reduces supply-chain risk. Drift detection (`--check`) lets an air-gapped site verify that transferred software matches the recorded BOM.
- **Licensing:** Public guidance.
- **Decision:** **LOCALIZE**. We claim alignment with the minimum elements that we populate, not certification.

### 2. MHA National Information Security Policy and Guidelines (NISPG), v5.0, 2014
- **Owner:** Ministry of Home Affairs, Cyber & Information Security Division.
- **URL:** https://www.mha.gov.in/en/divisionofmha/cyber-and-information-security-cis-division. The text used is the v5.0 PDF mirrored by government portals.
- **Type:** National policy.
- **Provides:**
  - Classification into Top Secret, Secret, Confidential, Restricted and Unclassified.
  - Key management:
    - a documented process;
    - logging of key operations;
    - keys stored in cryptographic hardware;
    - for sensitive networks, keys obtained from the **Joint Cipher Bureau (JCB)**;
    - **SAG-approved algorithms for Secret and Top Secret**.
  - Audit trail and log protection.
- **Relevance:** This is the governing handling policy for classified government information.
- **Access:** Public.
- **Online/offline:** Policy only.
- **Security implication:** Defines what production must meet. This prototype does **not** meet these points:
  - it doesn't use SAG-approved algorithms;
  - keys aren't obtained from JCB;
  - it uses a software keystore, not hardware.
- **Decision:** **REFERENCE**. The `classification` field (RESTRICTED, CONFIDENTIAL, SECRET or TOP SECRET) is the NISPG vocabulary and is bound into the authority-signed registration record; UNCLASSIFIED material doesn't need this system. The unmet points are listed as deployment gates.

### 3. CERT-In Cyber Security Directions No. 20(3)/2022, 28 Apr 2022, and FAQs
- **Owner:** CERT-In, under Section 70B(6) of the IT Act.
- **URL:** https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
- **Type:** Legal direction.
- **Provides:**
  - ICT clocks synchronised to NIC (`samay1.nic.in`, `samay2.nic.in`) or NPL (`time.nplindia.org`) NTP, or sources traceable to them;
  - logs kept securely for a rolling 180 days within India;
  - the time zone recorded with timestamps.
- **Relevance:** Timestamps in the ledger and audit trail are evidentiary.
- **Online/offline:** An air-gapped site cannot reach public NTP. It needs a local time server traceable to UTC(NPLI), for example a GNSS/NavIC-disciplined appliance.
- **Implemented:**
  - All timestamps are UTC ISO-8601 with an explicit offset.
  - `audit_events` is append-only (triggers), and no code path deletes it, so retention exceeds 180 days.
- **Decision:** **REFERENCE**. No runtime NTP call.

### 4. CERT-In Guidelines on Information Security Practices for Government Entities (29 Jun 2023)
- **Owner:** CERT-In.
- **URL:** https://www.cert-in.org.in/PDF/guidelinesgovtentities.pdf
- **Provides:**
  - 6.2.3: "No secret keys used by the application should be stored unencrypted";
  - a minimum 180-day log retention;
  - NIC/NPL NTP;
  - least privilege;
  - offline encrypted backups.
- **Relevance and implementation:** The encrypted keystore, role-based least privilege, and the append-only audit trail satisfy the *intent* of these clauses for this prototype.
- **Decision:** **REFERENCE**. No compliance claim.

### 5. TEC 910018:2025, Technical Report on Migration to Post-Quantum Cryptography (31 Jan 2025)
- **Owner:** Telecommunication Engineering Centre, DoT.
- **URL:** https://tec.gov.in/pdf/TR/Final%20technical%20report%20on%20migration%20to%20PQC%2028-03-25.pdf
- **Provides:**
  - the "harvest now, decrypt later" threat;
  - the need for a cryptographic inventory;
  - crypto-agility;
  - hybrid classical and PQC during migration.
- **Relevance:** Classified documents have long confidentiality lifetimes, so PQC key establishment is justified now.
- **Implemented:**
  - The CBOM is the cryptographic inventory.
  - Records carry version fields, which leaves room for algorithm agility.
- **Gap:** The prototype is PQC-only, not hybrid. See SECURITY.md.
- **Decision:** **REFERENCE**.

### 6. CSIR-NPL Indian Standard Time, UTC(NPLI)
- **Owner:** CSIR-National Physical Laboratory.
- **URL:** https://www.nplindia.org/index.php/science-technology/indian-standard-time-metrology-division/time-and-frequency-metrology-section/
- **Provides:** The national time scale, traceable to BIPM, disseminated through stratum-1 NTP servers (`time.nplindia.org`, `time1/2.nplindia.org`).
- **Decision:** **REFERENCE**. It is a deployment requirement for the local time source. A live NTP call would breach the air gap.

### 7. Controller of Certifying Authorities (CCA) / Root Certifying Authority of India (RCAI)
- **Owner:** MeitY, under the IT Act 2000 (§17, §18(b)).
- **URL:** https://www.cca.gov.in/rcai.html
- **Provides:**
  - the India PKI: licensed CAs issuing legally recognised Digital Signature Certificates (DSCs);
  - CRL publication and OCSP (`ocvs.gov.in`);
  - eSign;
  - regulated time stamping.
- **Relevance:** Legal non-repudiation of signatures.
- **Why not integrated:**
  - The India PKI issues classical (RSA/ECC) X.509 certificates, which don't certify ML-DSA-44 keys.
  - Revocation checking is online.
  - Adding a second, classical trust root would *weaken* the post-quantum property of attribution.
  - We must **not** claim that ML-DSA records are IT-Act digital signatures.
- **Production path:** A hybrid design could countersign trust manifests with a CCA-chain DSC, using locally snapshotted CRLs.
- **Decision:** **REFERENCE ONLY**.

### 8. API Setu (MeitY)
- **URL:** https://apisetu.gov.in ; the SOP is https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf
- **Type:** Online API marketplace implementing the MeitY Open API policy (2015).
- **Access:** Organisational onboarding with proof of identity, authority letter, organisation PAN, GST registration and certificate of incorporation. It then issues per-developer API keys, and provider approval is needed for each API.
- **APIs examined:** document/verification APIs (DigiLocker, PAN, GSTN and similar), aimed at citizen and business verification.
- **Evaluation:**
  1. No API relates to naval recipients, classified document provenance, or cryptographic attribution.
  2. Access is an online gateway with credentials, which conflicts with the air-gap requirement.
  3. Snapshotting identity responses into the enclave would import unrelated personal data.
- **Decision:** **REJECT**. Evaluated, but intentionally not integrated, because no relevant API exists and live access would violate the problem statement.

### 9. DigiLocker / Entity Locker / Meri Pehchaan (NeGD, MeitY)
- **URL:** https://apisetu.gov.in/digilocker
- **Provides:** Issuer, requester and authorised-partner APIs for citizen and entity documents, using OAuth 2.0 (PKCE), Aadhaar-based consent, and an India-hosted server requirement.
- **Why not integrated:**
  - Its documents are citizen credentials, not classified defence documents.
  - It is online only.
  - It introduces personal-data processing and new credentials.
- **Decision:** **REJECT**.

### 10. Open Government Data Platform (data.gov.in), NDSAP
- **URL:** https://data.gov.in ; licence at https://data.gov.in/sites/default/files/NDSAP_OpenDataLicense.pdf
- **Provides:** Shareable *non-sensitive* public datasets under the Government Open Data Licence–India, with attribution required. API access needs registration and a key.
- **Evaluation:** No dataset improves encryption, attribution, identity or provenance. Organisational and geographic datasets would be decorative.
- **Decision:** **REJECT**. No government dataset is required for the core system, because the problem is cryptographic and provenance-centric rather than data-dependent.

### 11. Digital Personal Data Protection Act 2023 and DPDP Rules 2025
- **Owner:** MeitY.
- **URL:** https://www.indiacode.nic.in/handle/123456789/22037
- **Relevance:** Recipient names are personal data (§2(t)). §17(2)(a) allows the Central Government to exempt notified State instrumentalities for security of the State; whether that applies is a legal determination we don't make.
- **Design response:**
  - The forensic marker contains **no personal data**; it is an opaque random token.
  - Names live only in the local registry.
  - Nothing leaves the system.
- **Decision:** **REFERENCE**. No compliance claim.

## Offline integration model

```text
OFFLINE CORE (encrypt, decrypt, watermark, sign, ledger, investigate)
      ↑ reads only
LOCAL TRUSTED DATA STORE   (trust_manifests table, append-only, re-verified on every read)
      ↑ import_package(): size → JSON → schema → pin → ML-DSA signature → version/revocation monotonicity
CONTROLLED DATA INGESTION  (signed package on removable media; POST /api/trust/import or provisioning script)
      ↑
AUTHORITATIVE SOURCE       (issuing authority WESEE HQ; production: its identity/PKI system)
```

| Source | Mode |
|---|---|
| Issuing-authority roster and keys | SIGNED DATA PACKAGE (periodic administrative import; revocation by new version) |
| CERT-In BOM guidelines | LOCAL ARTEFACT generated offline, with a checksum manifest for transfer |
| NISPG, CERT-In directions and guidelines, TEC, NPL, DPDP | REFERENCE-ONLY (requirements and deployment gates) |
| CCA/RCAI | REFERENCE-ONLY (possible future hybrid countersignature using local CRL snapshots) |
| API Setu, DigiLocker, data.gov.in | NOT INTEGRATED |

## Security impact of what was integrated

| Question | Signed trust manifest | SBOM/CBOM |
|---|---|---|
| Network dependency? | None | None |
| New credentials? | None. It uses the existing authority ML-DSA key | None |
| Privacy exposure? | Names and key fingerprints only, local | Package metadata only |
| New attack surface? | `/api/trust/import`: AUTHORITY only, 25 MB upload cap plus a 1 MB package cap, strict schema | Offline script |
| Supply-chain risk? | None added | Reduced (drift detection) |
| Stale data? | Older versions are rejected (`STALE`); revocations can't be undone | `--check` flags drift |
| Spoofing? | Pinned authority fingerprint plus ML-DSA signature | SHA256SUMS over BOM files |
| Availability dependency? | Core crypto is unaffected; attribution **fails closed** (`identity_trusted=false`) | None |
| Administrator trust? | The pin sits outside the data dir, and deleting the newest version is detected through the ledger. Whoever controls **both** the pin file and the data dir can still subvert it. | Whoever regenerates the BOM |
