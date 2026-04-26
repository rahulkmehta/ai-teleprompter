// Mic capture pipeline. Owns the getUserMedia stream + AudioContext + the
// pcm-worklet AudioWorkletNode. Each 50ms chunk of 16kHz Int16 PCM produced by
// the worklet is delivered to the consumer's onChunk callback as an
// ArrayBuffer; src/App.tsx forwards each chunk as a binary WebSocket frame
// to /ws, where the backend pipes it to Deepgram via DeepgramSTT.

export type ChunkHandler = (chunk: ArrayBuffer) => void;

export class PCMCapture {
  private context: AudioContext | null = null;
  private node: AudioWorkletNode | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;

  async start(onChunk: ChunkHandler): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });

    // Don't request a specific sample rate; let the device pick (usually 48kHz)
    // and let the worklet downsample. More portable across browsers.
    this.context = new AudioContext();
    await this.context.audioWorklet.addModule('/pcm-worklet.js');

    this.node = new AudioWorkletNode(this.context, 'pcm-worklet');
    this.node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      onChunk(event.data);
    };

    this.source = this.context.createMediaStreamSource(this.stream);
    this.source.connect(this.node);
    // Intentionally do NOT connect the node to context.destination — we don't
    // want to echo the mic back to the user's speakers.
  }

  async stop(): Promise<void> {
    this.node?.port.close();
    this.node?.disconnect();
    this.source?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    if (this.context && this.context.state !== 'closed') {
      await this.context.close();
    }
    this.node = null;
    this.source = null;
    this.stream = null;
    this.context = null;
  }
}
