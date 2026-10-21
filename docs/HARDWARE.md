# ReSpeaker Lite reference

Target: **Seeed reSpeaker Lite 2-Mic Array Voice Kit, SKU 110061601**, with XIAO ESP32-S3. Other ReSpeaker models need their own documentation.

Seeed's [recording example](https://wiki.seeedstudio.com/respeaker_record_and_play/) uses 16 kHz, two channels, 32-bit I2S slots, with the ESP32 as slave. The lab's network PCM is a separate 16-bit mono representation, not the raw I2S slot format.

| Signal | XIAO ESP32-S3 GPIO |
| --- | --- |
| BCLK | 8 |
| LRCLK / WS | 7 |
| Microphone data into ESP32 | 44 |
| ESP32 playback data out | 43 |
| XIAO user LED | 21, active low |

The user LED is separate from the XMOS RGB LED. For the 16 kHz capture path, the reference microphone firmware is **ReSpeaker Lite I2S v1.0.9**. Use Seeed's own [firmware directory](https://github.com/respeaker/reSpeaker_Lite/tree/master/xmos_firmwares) and [DFU guide](https://github.com/respeaker/reSpeaker_Lite/blob/master/xmos_firmwares/dfu_guide.md). Do not substitute USB-only firmware or another ReSpeaker model's image.

No firmware or flash command is included in this release. These notes are for hardware reference; the runnable lab uses generated tones only. It does not demonstrate microphone quality, physical radio reliability, provisioning, or encrypted device transport.
