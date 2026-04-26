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

    this.context = new AudioContext();
    await this.context.audioWorklet.addModule('/pcm-worklet.js');

    this.node = new AudioWorkletNode(this.context, 'pcm-worklet');
    this.node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      onChunk(event.data);
    };

    this.source = this.context.createMediaStreamSource(this.stream);
    this.source.connect(this.node);
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
