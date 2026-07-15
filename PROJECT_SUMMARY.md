# Project Overview: Church A/V Automation

## Background

Our church currently livestreams Sunday services over Zoom. Historically, a dedicated A/V operator manually controlled the entire system, including cameras, audio, Zoom, and recording. After that person moved away, volunteers began performing only the pre-service setup, while the minister operates without technical assistance during the service.

To reduce volunteer workload, one collaborator created a Python script using PyAutoGUI that automates the setup by reproducing the same mouse clicks and keyboard actions a human performs. While impressive, this approach is extremely brittle because it depends on window positions, UI layouts, timing delays, and screen contents. Minor software updates frequently break the automation.

The goal of this project is to replace that fragile automation with a maintainable, modular system that communicates with the underlying applications and hardware through stable APIs or protocols whenever possible.

This project is also intended to become a polished portfolio piece demonstrating software architecture, hardware/software integration, automation, and reliability engineering.

---

# Primary Goals

## Phase 1

Automate the Sunday service setup process.

The application should:

* Guide volunteers through any required physical setup.
* Verify that required hardware is available.
* Launch required applications.
* Configure the A/V system.
* Join the Zoom meeting.
* Configure Zoom.
* Start the OBS virtual camera.
* Verify audio routing.
* Perform health checks.
* Provide meaningful error messages instead of silently failing.

The application should prefer direct APIs over UI automation whenever possible.

---

## Phase 2

Provide one-click service control.

Examples:

* Prepare Worship
* Start Service
* End Service
* Shutdown

These operations should perform multiple coordinated actions while validating success after each step.

---

## Phase 3

Automate camera direction.

The church currently leaves a single wide-angle camera view active because no volunteer operates cameras during the service.

The long-term goal is automatic camera switching based on who is speaking.

Possible approaches include:

* microphone activity
* audio mixer levels
* camera presets
* computer vision
* speaker tracking

The preferred initial approach is audio-based switching using microphone activity rather than computer vision.

---

# Design Principles

## Reliability

The system should verify state rather than assume success.

For example:

Instead of:

"Clicked Start Virtual Camera"

Prefer:

"OBS reports Virtual Camera is running."

---

## Modularity

Separate the system into adapters.

Possible modules include:

* OBS Adapter
* Zoom Adapter
* Audio Mixer Adapter
* Camera Controller
* Workflow Engine
* Dashboard/UI
* Logging
* Configuration

The workflow should depend only on adapter interfaces rather than implementation details.

---

## Replace GUI Automation Incrementally

GUI automation should be treated as a last resort.

Whenever an application exposes an API, SDK, OSC interface, WebSocket, MIDI, CLI, or network protocol, that should be preferred.

If PyAutoGUI remains necessary for some operations, isolate it behind a single adapter so it can later be replaced without affecting the rest of the application.

---

## State-Based Workflows

Model actions in terms of desired system state rather than mouse clicks.

For example:

```
ensure OBS is connected

ensure Virtual Camera is running

ensure Zoom meeting joined

ensure Zoom recording active

ensure required mixer channels unmuted

ensure output routed to Zoom
```

---

## User Experience

Volunteers should not need to understand OBS, Zoom internals, or audio routing.

The application should present simple workflows such as:

```
□ Projector ready

□ OBS connected

□ Audio mixer connected

□ Zoom joined

□ Cameras ready

□ Audio verified

□ Recording ready

[ Prepare Worship ]
```

During service:

```
Recording

Camera Mode:
Automatic

Current Speaker:
Pulpit

[ Manual Override ]
```

---

# Current Known Components

Known software:

* OBS Studio
* Zoom
* XAir mixer software

Additional hardware and software details will be gathered during development.

---

# Repository Goals

This project should demonstrate:

* clean architecture
* interface-driven design
* dependency inversion
* robust error handling
* hardware/software integration
* logging
* testing
* configuration management
* maintainability

The resulting repository should be understandable by other developers and suitable as a professional portfolio project.

---

# Initial Milestone

Before automating anything, create a read-only system validator.

The validator should detect and report:

* required software running
* OBS connection
* XAir connection
* current OBS scene
* virtual camera status
* mixer connectivity
* audio routing status
* missing dependencies

No settings should be modified during this phase.

The first milestone should focus entirely on discovering available APIs, replacing assumptions with verification, and creating a reliable foundation for later automation.
