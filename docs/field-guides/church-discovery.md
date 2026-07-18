# Church on-site discovery field guide

Use this guide to replace assumptions with sanitized, reviewable facts before the Sunday service.
Discovery records observations only. Do not change production settings merely to complete the
worksheet, and never copy actual secrets into notes, fixtures, profiles, issues, or chat.

## Before starting

Record the date, observer, workstation asset label, and whether the system is in rehearsal or a
maintenance window. Obtain permission before connecting test cables or sending read-only network
queries. Keep two separate artifacts:

1. **Facts to record** are the sanitized values that may inform the site profile or fixtures.
2. **Commands/procedures to run** are local discovery steps. Record their sanitized results, not
   credentials exposed by tools or dialogs.

## Windows workstation

**Facts to record**

- Windows edition and full OS build.
- Account permission level used for Wortava (`standard user` or `administrator`); do not record
  the username or other personal data.

**Commands to run**

- Open **Settings > System > About** and transcribe edition and OS build.
- Open a normal PowerShell window and run `whoami /groups`; record only whether the process is
  standard or elevated. Do not retain account/domain names from the output.

## OBS Studio

**Facts to record**

- OBS version.
- Whether WebSocket is enabled; configured host/interface and port; whether authentication is
  enabled (yes/no only—never the password).
- Current scene collection and the expected program scene for Sunday service.
- Virtual-camera behavior: expected state before service, how it is started, which consumer uses
  it, and the observed active/inactive state during the physical test.

**Commands/procedures to run**

- In OBS, use **Help > About** for the version, **Scene Collection** for the active collection,
  and **Tools > WebSocket Server Settings** for enabled/host/port/authentication state.
- Read the current Program scene name from OBS. With an operator present, follow the normal
  service procedure for the virtual camera and confirm its video in the intended consumer.
- Do not reveal, copy, screenshot, or test with the WebSocket password in discovery notes.

## Zoom

**Facts to record**

- Zoom version, installation path, and running process name.
- Account type (for example Basic, Pro, Business, or organization-managed) without account name,
  email, meeting ID, passcode, token, or tenant identifiers.
- Evidence for any vendor-supported control API available to this installed client/account:
  product/document name, version/date, URL or local documentation reference, and supported scope.
  Record `none confirmed` when no authoritative evidence is found.

**Commands/procedures to run**

- Use Zoom's **About** dialog for version/account tier, Windows Apps/Installed Apps and file
  properties for install path, and Task Manager **Details** for the process name.
- Consult official Zoom documentation supplied for the site. Do not probe undocumented endpoints,
  automate the UI, join a meeting, or capture meeting credentials.

## X Air mixer and network

**Facts to record**

- Exact X Air model and firmware version.
- X Air Edit version and executable path.
- Mixer IP address and OSC port.
- Network topology: workstation connection, switch/access-point/router roles, wired/wireless path,
  relevant sanitized subnet/VLAN description, and whether addressing is static or DHCP.
- Sanitized `/info` OSC response, preserving message address and safe model/version fields.
- Sanitized OSC capture sufficient to establish protocol/addressing behavior.

**Commands/procedures to run**

- Read model/firmware from the mixer/X Air Edit information view and version/path from X Air Edit
  About/file properties. Read IP/port and topology from the approved site configuration and
  network owner; do not change them.
- From the workstation and with network-owner approval, send the documented read-only OSC
  `/info` query to the recorded mixer IP/port and save only the sanitized response.
- If a packet capture is approved, limit it to the shortest useful mixer exchange, apply an OSC
  host/port filter, sanitize it using the checklist below, and delete the unsanitized working copy
  according to site policy. Never issue write/control OSC messages during discovery.

## Windows render and capture audio

**Facts to record**

- Every active render endpoint's complete endpoint ID and friendly name.
- Every active capture endpoint's complete endpoint ID and friendly name.
- Which endpoint holds the default multimedia role and which holds the default communications
  role for both render and capture.
- Whether each confirmed endpoint is expected to hold each role; record these booleans as
  `expected_<direction>_default_multimedia` and
  `expected_<direction>_default_communications` in the site profile.
- Per-application routing observations for OBS, Zoom, X Air Edit, and other service-critical apps:
  selected input/output or system default, and whether the assignment is observable or unknown.
- Results of the physical signal test below, including each step's expected and actual outcome.

**Commands/procedures to run**

- Use Windows **Settings > System > Sound**, **More sound settings**, and **Volume mixer** to
  inventory active endpoints, default roles, and visible per-application routing. Use an approved
  read-only Core Audio inventory tool if complete endpoint IDs are not displayed by Settings.
- Do not infer per-application routing that Windows does not expose; record `unknown` with the
  observation boundary.

**Physical signal test procedure**

1. Confirm the required physical connections listed in the next section, normal mixer routing,
   safe monitoring level, and operator approval.
2. Send a known, non-sensitive test source into the expected mixer input. Confirm meter activity
   at the mixer input and intended bus/output without changing the service configuration.
3. Confirm the expected Windows capture endpoint receives the signal; then confirm OBS meters and
   a short local test recording contain it. Do not stream or join a live meeting.
4. Start the OBS virtual camera using the normal operator procedure and confirm the expected OBS
   program image in Zoom's local video preview without joining a meeting.
5. Play a known test tone locally through the expected Windows render endpoint and confirm it
   reaches the intended mixer return and approved physical monitor/output.
6. Stop test media and restore only the normal operator-controlled transient state used by the
   procedure. Record PASS/FAIL and the exact failed boundary for every step.

## Physical connections and Sunday readiness

**Facts to record**

Create a row for every required connection: source device/port, cable or network medium, destination
device/port, purpose, expected link/signal indication, observed indication, and PASS/FAIL. At
minimum cover mixer-to-workstation USB/audio, workstation display/control connections, mixer
Ethernet/Wi-Fi path, camera/capture path, program/monitor outputs, and power for each required
device. Add site-specific microphones, amplifiers, projectors, and adapters.

The pre-Sunday expected pass state is: all required devices powered and identified; every required
physical connection seated and showing its expected link/signal; OBS, Zoom, and X Air Edit at the
recorded versions/paths and expected processes available; OBS WebSocket reachable with
authentication enabled where configured; correct scene collection/program scene; virtual camera
behaving as documented; mixer responding to read-only `/info`; expected render/capture endpoints
active with correct default roles/routing observations; and every physical signal-test step PASS.
Any failed required connection or test step is a **no-go/FAIL** until an authorized operator fixes
and retests it. Unknown facts remain explicitly `UNKNOWN`, not assumed PASS.

## Sanitization checklist

Before creating a fixture, profile, report attachment, issue, or shared discovery note:

- Remove all passwords, OBS WebSocket secrets, API keys/tokens, cookies, and authentication headers.
- Remove Zoom meeting IDs, passcodes, join links, webinar/meeting credentials, and account emails.
- Remove personal names, usernames, email addresses, phone numbers, participant data, chat, video,
  audio, filenames containing personal data, and other personal data.
- Remove Wi-Fi SSIDs when site-sensitive, Wi-Fi passwords/PSKs, router/admin credentials, and
  private keys/certificates.
- Remove unrelated packet payloads and device identifiers such as MAC addresses or serial numbers
  unless the site explicitly approves a documented need; replace them with stable placeholders.
- Keep only the minimum mixer IP/topology and OSC fields needed for validation; replace unrelated
  hosts and routable public addresses with descriptive placeholders.
- Search the sanitized artifact for the original sensitive values, credential-shaped strings, and
  meeting URLs. Have a second person review it before committing or sharing.
- Store actual credentials only in the site's approved secret store. Fixtures use unmistakably fake
  values and must never be derived by lightly editing a real secret.
