import { useState } from "react";
import "./App.css";
import Lottie  from 'lottie-react';
import animationData from './ani.json';
import TextToSpeech from "./components/TextToSpech";
import AlertDisplay from "./components/AlertDisplay";

function App() {
  const [count, setCount] = useState(0);

  return (
    <>
      <div style={{ width: 200, height: 200 }}>
        <Lottie animationData={animationData} loop={true} />
        {/* <TextToSpeech/> */}
        <AlertDisplay/>
      </div>
    </>
  );
}

export default App;
