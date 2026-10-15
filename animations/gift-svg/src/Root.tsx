import {Composition} from 'remotion';
import {DrawingScene, FPS, FRAMES} from './Scene';
export const RemotionRoot = () => <Composition id="PeppaDrawing" component={DrawingScene} durationInFrames={FRAMES} fps={FPS} width={1280} height={720}/>;
