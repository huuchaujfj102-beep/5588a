import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
export const AuditDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, 76, 89], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{backgroundColor: '#10231f', color: '#f0e5c9', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif'}}>
    <div style={{opacity, textAlign: 'center', padding: 80}}>
      <div style={{fontSize: 76, fontWeight: 700}}>影视审核工作站</div>
      <div style={{fontSize: 42, marginTop: 42}}>Remotion 渲染测试</div>
      <div style={{fontSize: 30, marginTop: 20}}>5588a · 1080 × 1920 · 30 FPS</div>
    </div>
  </AbsoluteFill>;
};
