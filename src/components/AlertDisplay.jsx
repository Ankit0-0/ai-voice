import { useState, useEffect, useCallback } from 'react';
import { Alert, AlertTitle, Snackbar } from "@mui/material";
import { Bell, WifiOff } from 'lucide-react';

const AlertDisplay = () => {
  const [alerts, setAlerts] = useState([]);
  const [ws, setWs] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [connectionError, setConnectionError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const MAX_RETRIES = 5;

  const handleSpeak = useCallback((message) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, []);

  const connectWebSocket = useCallback(() => {
    try {
      // Update connection status
      setConnectionStatus('connecting');
      
      const websocket = new WebSocket('ws://localhost:8000/ws');
      
      websocket.onopen = () => {
        console.log('WebSocket Connected');
        setConnectionStatus('connected');
        setConnectionError(false);
        setRetryCount(0);
      };
      
      websocket.onmessage = (event) => {
        try {
          const alertData = JSON.parse(event.data);
          setAlerts(prevAlerts => [
            alertData,
            ...prevAlerts.slice(0, 9)
          ]);
          handleSpeak(alertData.message);
        } catch (error) {
          console.error('Error processing message:', error);
        }
      };

      websocket.onclose = (event) => {
        console.log('WebSocket Disconnected:', event);
        setConnectionStatus('disconnected');
        setWs(null);

        // Implement exponential backoff for reconnection
        if (retryCount < MAX_RETRIES) {
          const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
          setTimeout(() => {
            setRetryCount(prev => prev + 1);
            connectWebSocket();
          }, timeout);
        } else {
          setConnectionError(true);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError(true);
        setConnectionStatus('error');
      };

      setWs(websocket);
    } catch (error) {
      console.error('Connection error:', error);
      setConnectionError(true);
      setConnectionStatus('error');
    }
  }, [handleSpeak, retryCount]);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (ws) {
        ws.close();
        setWs(null);
      }
      window.speechSynthesis.cancel();
    };
  }, [connectWebSocket]);

  const getAlertSeverity = (type) => {
    switch (type) {
      case 'person':
        return 'info';
      case 'car':
        return 'warning';
      case 'dog':
        return 'success';
      case 'pet_owner':
        return 'success';
      default:
        return 'info';
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  const handleRetryConnection = () => {
    setRetryCount(0);
    setConnectionError(false);
    connectWebSocket();
  };

  return (
    <>
      <div className="fixed right-4 top-4 w-96 space-y-4 z-50">
        {/* Connection Status Indicator */}
        {connectionStatus !== 'connected' && (
          <Alert 
            severity="warning" 
            className="mb-4"
            action={
              connectionError ? (
                <button
                  onClick={handleRetryConnection}
                  className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Retry
                </button>
              ) : null
            }
          >
            <AlertTitle className="flex items-center gap-2">
              <WifiOff className="h-4 w-4" />
              Connection Status
            </AlertTitle>
            {connectionStatus === 'connecting' ? 'Connecting to server...' : 
             connectionStatus === 'error' ? 'Connection failed' : 
             'Disconnected from server'}
          </Alert>
        )}

        {/* Alerts */}
        {alerts.map((alert, index) => (
          <Alert 
            key={`${alert.timestamp}-${index}`}
            severity={getAlertSeverity(alert.type)}
            icon={<Bell className="h-4 w-4" />}
            className="shadow-lg backdrop-blur-sm bg-opacity-95"
            sx={{
              '& .MuiAlert-message': {
                width: '100%'
              },
              animation: 'slideIn 0.3s ease-out',
            }}
          >
            <AlertTitle className="font-semibold">
              {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)} Detected
            </AlertTitle>
            <div className="space-y-1">
              <p className="text-sm">{alert.message}</p>
              <p className="text-xs text-gray-500">
                {formatTimestamp(alert.timestamp)} - {alert.position} side
              </p>
            </div>
          </Alert>
        ))}
      </div>

      {/* Connection Error Snackbar */}
      <Snackbar
        open={connectionError}
        autoHideDuration={6000}
        onClose={() => setConnectionError(false)}
      >
        <Alert 
          severity="error" 
          onClose={() => setConnectionError(false)}
        >
          Unable to connect to server. Please check if the server is running.
        </Alert>
      </Snackbar>

      <style jsx global>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default AlertDisplay;