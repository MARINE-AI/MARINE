import React, { useState, useEffect } from 'react';

interface FileStatusProps {
    status: 'idle' | 'loading' | 'success' | 'error';
}

const FileStatus: React.FC<FileStatusProps> = ({ status }) => {
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        let interval: NodeJS.Timeout | null = null;

        if (status === 'loading') {
            setProgress(0);
            interval = setInterval(() => {
                setProgress((prev) => (prev < 100 ? prev + 10 : 100));
            }, 500);
        } else if (status === 'idle' || status === 'error') {
            setProgress(0);
        } else if (status === 'success') {
            setProgress(100);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [status]);

    const getStatusMessage = () => {
        switch (status) {
            case 'idle': return 'Idle';
            case 'loading': return 'Uploading...';
            case 'success': return 'Upload Successful!';
            case 'error': return 'Upload Failed!';
            default: return '';
        }
    };

    return (
        <div style={{ width: '100%', textAlign: 'center', fontSize: '14px' }}>
            <div>{getStatusMessage()}</div>
            {status === 'loading' && (
                <div style={{ width: '100%', backgroundColor: '#ddd', borderRadius: '5px', marginTop: '5px' }}>
                    <div
                        style={{
                            width: `${progress}%`,
                            height: '10px',
                            backgroundColor: '#4caf50',
                            transition: 'width 0.5s ease-in-out',
                        }}
                    ></div>
                </div>
            )}
        </div>
    );
};

export default FileStatus;
