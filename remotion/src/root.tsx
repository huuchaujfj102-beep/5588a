import React from 'react';
import {Composition} from 'remotion';
import {AuditDemo} from './scene';
export const Root: React.FC = () => <Composition id="AuditDemo" component={AuditDemo} durationInFrames={450} fps={30} width={1080} height={1920} />;
