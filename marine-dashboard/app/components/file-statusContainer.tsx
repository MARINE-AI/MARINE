import React, { useState } from 'react';
import FileStatus from './file-status';

const FileStatusContainer: React.FC = () => {
    const [isVisible, setIsVisible] = useState(true);
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

    const handleClose = () => setIsVisible(false);

    if (!isVisible) return null; // Ensure it always returns a valid ReactNode

    return (
        <div style={{ position: 'fixed', top: 0, width: '100%', zIndex: 1000 }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#fff',
                padding: '10px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                borderRadius: '5px'
            }}>
                <FileStatus status={status} />
                <button
                    onClick={handleClose}
                    style={{
                        marginLeft: '10px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '16px'
                    }}
                >
                    ✖
                </button>
            </div>
        </div>
    );
};

export default FileStatusContainer;
