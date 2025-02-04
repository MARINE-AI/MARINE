import React, { useState } from 'react';
import FileStatus from './file-status';

const FileStatusContainer: React.FC = () => {
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  return (
    <div style={{ position: 'fixed', top: 0, width: '100%', zIndex: 1000 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff', padding: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderRadius: '5px' }}>
        <FileStatus />
        <button onClick={() => setVisible(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}>✖</button>
      </div>
    </div>
  );
};

export default FileStatusContainer;
