import { useState, useEffect } from "react";
import "./Monitoramento.css";

const API_VIDEO_FEED_URL = "http://192.168.0.77:4545/";

const Monitoramento = () => {
  const [isOnline, setIsOnline] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_VIDEO_FEED_URL}/status`);
        const data = await response.json();
        setIsOnline(data.camera_aberta);
      } catch (error) {
        setIsOnline(false);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="monitoramento-container">
      <div className="monitoramento-header">
        <h1>Monitoramento</h1>
        <div className="status-indicator">
          <div className={`status-dot ${isOnline ? "online" : "UFAM"}`}></div>
          <span>{isOnline ? "Online" : "UFAM"}</span>
        </div>
      </div>

      <div className="video-container">
        <img
          src={`${API_VIDEO_FEED_URL}/video_feed`}
          alt="Camera Feed"
          className="video-feed"
        />
      </div>
    </div>
  );
};

export default Monitoramento;