# Current Sanctuary A/V State

## Purpose

This document describes how the sanctuary audiovisual system is currently used.

It is not intended to reproduce the original system design or every capability of the installed equipment. Instead, it records:

- the workflows currently used during Sunday worship
- assumptions that have changed since the original system was designed
- operational limitations that affect automation
- the current staffing model
- the boundaries of the WORTAVA project

The original system documentation remains useful as historical and technical reference material, but it should not be treated as an exact description of current practice.

## Security and Repository Policy

This handbook must not contain production secrets or authentication information.

Do not commit:

- passwords
- Zoom host keys
- Zoom meeting credentials
- API tokens
- OAuth credentials
- OBS WebSocket passwords
- Wi-Fi credentials
- router or switch credentials
- Windows security-question answers
- private recording links
- personally identifying information about worship participants
- unredacted production configuration files containing secrets

Application secrets must be supplied through environment variables, ignored local configuration files, or an approved secrets-management mechanism.

Example configuration files may document required fields, but must contain placeholders rather than live values.

Network addresses should be represented with descriptive names or placeholders unless a specific address is required for development and has been explicitly approved for inclusion in the repository.

Even when the repository is private, committed secrets must be treated as exposed.

## Historical Context

The sanctuary A/V system was originally designed for hybrid worship during and after the COVID-19 pandemic.

The original requirements assumed that a dedicated Worship Technician would operate the system during services. That technician would manage cameras, audio, Zoom, slides, and transitions between different worship scenarios.

For a period, a part-time employee operated the system manually from the worship technology booth behind the pulpit. This included selecting contextual camera views during the service.

After that employee moved away in December, the minister temporarily handled the A/V workflow herself. She started the Zoom meeting at the beginning of the service and left the camera on a wide sanctuary view rather than changing shots throughout worship.

Operating the service and the A/V system simultaneously proved impractical.

The church subsequently created a volunteer rotation. Volunteers currently perform setup before the service but are not expected to remain at the console during worship.

This change in staffing is the primary reason the automation project exists.

## Current Staffing Model

The current operating model assumes:

- a volunteer is available before the service
- the volunteer can complete physical setup tasks
- the volunteer can start and verify the sanctuary A/V systems
- the volunteer does not remain at the worship technology booth throughout the service
- the minister and other worship leaders should not be responsible for technical operation during worship
- the system should require little or no interaction once the service begins

The original assumption of a dedicated in-service Worship Technician is no longer valid.

Any new automation must be designed around unattended or minimally attended operation.

## Current Worship Scenarios

The original system requirements describe several possible A/V scenarios. Only a subset is currently used during normal Sunday worship.

### Live Sanctuary Speaker

A person speaks or performs in the sanctuary.

Typical locations and audio sources include:

- pulpit
- lectern
- center or front of sanctuary
- piano
- handheld microphone
- wearable microphone
- choir area
- other established microphone locations

Sanctuary microphones feed the audio mixer.

Sanctuary cameras feed OBS Studio.

OBS provides a virtual camera source to Zoom.

This is the primary scenario the automation project must support.

### Google Slides Without Audio

Slide decks are normally operated from a worship leader's laptop.

The laptop casts the presentation through Chromecast to the ceiling-mounted sanctuary projector.

The presenter controls slide advancement from the laptop or an associated presentation remote.

The projector is not connected to the sanctuary speaker system.

The current workflow therefore assumes that slide presentations do not require audio playback through the sanctuary sound system.

## Slide Presentation Limitations

There is currently no clean, standard audio path from a presenter laptop to the sanctuary speakers.

Audio associated with a presentation could theoretically be handled in one of two ways.

### Worship Booth Playback

The presentation could be run from the worship technology booth.

This could allow audio to be routed through the booth's A/V system, but it would require a technician to operate the slides during the service.

That conflicts with the current staffing model.

### Laptop Playback Into a Microphone

A presenter could play laptop audio near the lectern microphone.

This requires little additional setup, but produces degraded sound quality and may create inconsistent volume, feedback, or intelligibility problems.

This is not considered a reliable production workflow.

### Current Assumption

Normal Sunday slide decks should not contain audio that must be reproduced through the sanctuary sound system.

Supporting high-quality presentation audio may be considered as a future infrastructure project, but it is not an initial WORTAVA requirement.

## Zoom Usage

Zoom is the church's live remote-participation platform for Sunday worship.

The sanctuary system currently:

- joins the established Sunday worship meeting
- claims host privileges
- configures participant mute permissions
- sends OBS video to Zoom through the OBS virtual camera
- sends the sanctuary audio mix to Zoom
- records the service to the cloud
- ends the meeting after worship

Remote attendees receive the live sanctuary service through Zoom.

The automation project should initially support the existing Zoom workflow rather than replacing Zoom.

Some Zoom operations may not expose stable external controls through the desktop client. Any unavoidable GUI automation should be isolated behind a dedicated adapter and treated as replaceable technical debt.

## Camera Operation

The sanctuary has two ceiling-mounted PTZ cameras.

The cameras are capable of:

- pan
- tilt
- optical zoom
- network control
- recalling predefined positions
- providing close, medium, and wide views

OBS includes configured camera controls and named presets for common worship locations and scenarios.

Historically, a technician changed camera framing during the service.

Under the current volunteer model, no operator remains at the console. The service therefore normally uses a wide camera view for most or all of worship.

This preserves coverage but does not take advantage of the installed cameras' close-up and contextual framing capabilities.

A major future goal of the project is to restore contextual camera direction without requiring a dedicated operator.

## Automatic Camera Direction

The preferred initial strategy for automatic camera direction is microphone-driven preset selection.

The audio mixer exposes distinct channels for known speaking and performance locations. Possible mappings include:

- pulpit microphone to pulpit camera preset
- lectern microphone to lectern camera preset
- piano input or microphone to piano preset
- choir or overhead microphones to choir or wide preset
- handheld microphone to a suitable center or wide preset
- wearable microphone to a configurable mobile-speaker view

The camera director should use audio activity as evidence of the current speaker or worship location.

The initial design should not depend on facial recognition or identity detection.

Computer vision may later be used to refine framing, but it should not be required for the first automatic camera-director implementation.

### Camera Switching Guardrails

Automatic switching must avoid distracting or unstable behavior.

The system should eventually support rules such as:

- require sustained microphone activity before switching
- ignore brief noises, coughing, handling noise, and isolated peaks
- enforce a minimum shot duration
- avoid rapid switching between microphones
- retain the current shot when competing signals are too similar
- use a wide shot when several locations are active
- return to a safe wide shot when speaker location is uncertain
- allow a human to disable automation
- allow a human to lock the current shot
- provide manual preset controls as a fallback

Exact thresholds and timing values must be tested in the sanctuary rather than assumed during development.

## Audio Operation

The Behringer X Air XR16 is the sanctuary's network-controlled digital audio mixer.

The current setup includes named channels for established microphones and inputs.

The manual workflow includes verifying that required channels and outputs have the expected mute state.

Audio automation should be introduced conservatively.

The first implementation should read and report mixer state without changing it.

Later phases may apply a known Sunday configuration, but changes affecting amplification or output routing should include:

- validation
- clear logging
- safe defaults
- error handling
- manual override
- protection against feedback or unexpectedly high output

A failed camera operation is inconvenient. A failed audio operation can disrupt worship or create unsafe sound levels. Audio control therefore requires stricter safeguards.

## OBS Operation

OBS Studio handles sanctuary video production.

Its current responsibilities include:

- receiving feeds from both PTZ cameras
- providing preview and program views
- switching or transitioning between camera sources
- exposing configured PTZ controls
- providing the virtual camera consumed by Zoom

OBS supports WebSocket control and should be integrated through that interface rather than through mouse-coordinate automation.

The application should eventually be able to:

- verify that OBS is available
- verify the active scene
- start and stop the virtual camera
- select or transition scenes
- inspect relevant source state
- report connection and operation errors

## Projector Operation

The ceiling-mounted projector displays content inside the sanctuary.

In the current workflow:

- the projector is powered on manually
- the correct HDMI input is selected manually when necessary
- slide decks are cast from a worship leader's laptop
- the projector is powered off manually after the service
- the projection screen is operated manually

Physical projector and screen operations are outside the initial automation boundary.

The application may present them as checklist items.

Future automation could investigate infrared control, network control, smart power, or projector-state monitoring, but those features are not part of the first milestone.

## YouTube Workflow

The church does not livestream Sunday services directly to YouTube.

The live service is recorded through Zoom.

On Sunday afternoon, the recording is edited before being uploaded to YouTube.

The editing process removes:

- copyrighted material
- the Sharing of Joys and Concerns portion
- any other content that should not be included in the public recording

The automation project must not automatically publish an unedited service recording.

The system should preserve a recording suitable for the existing post-service editing workflow.

Automated editing support may be considered later, but publication should remain a deliberate human action.

## Privacy and Copyright

The Sharing of Joys and Concerns is intentionally removed before public distribution.

The system must not treat the Zoom recording and the public YouTube video as equivalent artifacts.

Potential future recording workflows should distinguish among:

- live Zoom participation
- private or restricted cloud recording
- editing source material
- final public recording

Any automated recording or publishing feature must account for privacy, pastoral sensitivity, and copyright restrictions.

## Current Manual Responsibilities

The following tasks are currently performed before worship:

- turn on the relevant power strip
- lower or verify the projection screen
- turn on the projector
- select the correct projector input
- start the sanctuary computers
- sign in to the required accounts
- open OBS Studio
- open X Air Edit
- open Zoom
- join the Sunday Zoom meeting
- claim host privileges
- configure participant mute behavior
- start the OBS virtual camera
- verify the camera view
- verify required mixer channels and outputs
- join Zoom from secondary sanctuary locations
- test remote audio and video
- start cloud recording shortly before worship

After worship, the operator:

- stops the Zoom recording
- ends the Zoom meeting
- stops the OBS virtual camera
- closes the applications
- shuts down the computers
- powers down the projector
- turns off the relevant power strip

Some of these actions can be replaced with direct software integrations. Others require physical confirmation or may remain manual.

## Automation Boundaries

### Initial In Scope

The project should initially focus on:

- detecting required software and devices
- checking connectivity
- reading current system state
- validating expected Sunday configuration
- reporting actionable errors
- starting and stopping the OBS virtual camera
- controlling OBS through its WebSocket interface
- reading XR16 mixer state
- controlling PTZ cameras through supported network protocols
- exposing simple manual camera preset controls
- recording structured diagnostic logs

### Later In Scope

Possible later features include:

- one-button service preparation
- guarded mixer configuration
- automated Zoom setup
- automatic camera direction
- service-state workflows
- timed recording prompts or controls
- manual override controls
- unattended health monitoring
- post-service diagnostic reports
- assisted recording preparation for editing

### Out of Scope for the Initial Project

The initial project will not attempt to:

- automate public YouTube publishing
- livestream directly to YouTube or Facebook
- reproduce copyrighted material publicly
- publish the Sharing of Joys and Concerns
- replace the church's slide-presentation workflow
- provide high-quality laptop presentation audio
- physically lower the projection screen
- physically operate the projector remote
- replace all Zoom desktop behavior immediately
- use facial recognition
- identify individual worship participants
- make irreversible audio changes without validation and safeguards

## Design Implications

The project should be designed as a control system rather than a sequence of simulated clicks.

Core components will likely include:

- workflow engine
- OBS adapter
- XR16 adapter
- PTZ camera adapter
- Zoom adapter
- camera director
- system validator
- configuration loader
- logging and diagnostics
- volunteer-facing dashboard

Each adapter should expose desired capabilities and state rather than UI coordinates.

Examples:

```python
obs.ensure_virtual_camera_running()
mixer.get_channel_level("LCTRN")
camera.recall_preset("Lectern")
zoom.get_meeting_state()