// AudioWorkletProcessor that turns mic audio into 16kHz Int16 PCM chunks.
//
// Loaded once per session by src/audio.ts via audioContext.audioWorklet.addModule().
// The processor's process() runs in the high-priority audio thread on every
// 128-sample quantum. It downsamples from the AudioContext's native rate
// (typically 48kHz) to 16kHz using box-filter averaging (cheap anti-aliasing),
// converts Float32 [-1,1] to Int16, accumulates ~50ms chunks (800 samples),
// and posts each chunk's ArrayBuffer to the main thread (transferred to avoid
// copy). The main thread forwards each chunk as a binary WebSocket frame to
// the backend, which feeds it to Deepgram.

const TARGET_SAMPLE_RATE = 16000;
const CHUNK_SAMPLES = 320; // 20ms at 16kHz — smaller chunks = lower capture latency

class PCMWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / TARGET_SAMPLE_RATE; // global `sampleRate` = ctx rate
    this.tail = new Float32Array(0); // unprocessed samples from last quantum
    this.outBuffer = new Int16Array(CHUNK_SAMPLES);
    this.outIndex = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;
    const channel = input[0];

    // Append the new quantum to whatever didn't divide evenly last time.
    const merged = new Float32Array(this.tail.length + channel.length);
    merged.set(this.tail);
    merged.set(channel, this.tail.length);

    // Box-filter downsample: each output sample is the mean of the input
    // samples that fall in its bin. Cheap anti-aliasing without an FIR.
    const outCount = Math.floor(merged.length / this.ratio);
    let consumedThroughIndex = 0;

    for (let i = 0; i < outCount; i++) {
      const start = Math.floor(i * this.ratio);
      const end = Math.floor((i + 1) * this.ratio);
      let sum = 0;
      let n = 0;
      for (let j = start; j < end && j < merged.length; j++) {
        sum += merged[j];
        n++;
      }
      const sample = n > 0 ? sum / n : 0;
      const clamped = sample < -1 ? -1 : sample > 1 ? 1 : sample;
      this.outBuffer[this.outIndex++] = (clamped * 0x7fff) | 0;

      if (this.outIndex >= CHUNK_SAMPLES) {
        // Transfer the buffer rather than copy. After transfer, this.outBuffer
        // is detached on the main thread — allocate a fresh one.
        const chunk = this.outBuffer.buffer;
        this.port.postMessage(chunk, [chunk]);
        this.outBuffer = new Int16Array(CHUNK_SAMPLES);
        this.outIndex = 0;
      }

      consumedThroughIndex = end;
    }

    // Stash the unprocessed remainder for the next quantum.
    this.tail = merged.slice(consumedThroughIndex);
    return true;
  }
}

registerProcessor('pcm-worklet', PCMWorklet);
