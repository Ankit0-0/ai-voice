import React, { useState } from 'react';

const TextToSpeech = () => {
  const [text, setText] = useState(`Potato, potato, you’re the star today,
Potato, potato, in every way!
Baked potato, mashed potato, fries galore,
Potato, potato, who could ask for more?

Potato, potato, so golden and fried,
Potato, potato, I’m on a ride!
Potato, potato, in every dish,
Potato, potato, fulfill my wish!

Potato, potato, boiled or mashed,
Potato, potato, my love’s unmatched!
Potato, potato, I can’t get enough,
Potato, potato, you’re the stuff!`);

  const handleSpeak = () => {
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div>
      {/* <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type something to speak"
      /> */}
      <button onClick={handleSpeak}>Speak</button>
    </div>
  );
};

export default TextToSpeech;
