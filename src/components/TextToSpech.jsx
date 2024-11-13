import React, { useState, useEffect } from 'react';

const TextToSpeech = () => {
  const [text, setText] = useState('');

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:6789"); 

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const alertText = data.alerts ? data.alerts.join(', ') : 'No alerts';
      setText(alertText);
      handleSpeak(alertText);  
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleSpeak = (message) => {
    const utterance = new SpeechSynthesisUtterance(message);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div>
      <h2>Alert: {text}</h2>
      <button onClick={() => handleSpeak(text)}>Speak</button>
    </div>
  );
};

export default TextToSpeech;
