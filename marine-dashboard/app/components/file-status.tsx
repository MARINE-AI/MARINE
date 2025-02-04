import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';

interface FileStatusProps {
  initialStatus?: string;
}

const FileStatus: React.FC<FileStatusProps> = ({ initialStatus = "Waiting for updates..." }) => {
  const [status, setStatus] = useState(initialStatus);
  const { data: session } = useSession();

  useEffect(() => {
    if (!session || !session.user || !session.user.email) {
      console.error("No user session available for SSE connection.");
      return;
    }
    const userEmail = session.user.email;
    const eventSource = new EventSource(`http://localhost:8080/sse?user_email=${encodeURIComponent(userEmail)}`);

    eventSource.onmessage = (e) => {
      setStatus(e.data);
    };

    eventSource.onerror = (e) => {
      console.error("SSE error:", e);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [session]);

  return (
    <div style={{ padding: "10px", background: "#f0f0f0", borderRadius: "5px" }}>
      <strong>Status:</strong> {status}
    </div>
  );
};

export default FileStatus;
