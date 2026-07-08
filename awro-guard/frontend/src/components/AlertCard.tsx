import { AlertCircle, ShieldAlert } from "lucide-react";

interface AlertProps {
  type: string;
  priority: string;
  camera_id: string;
  confidence: number;
}

const AlertCard = ({ type, priority, camera_id, confidence }: AlertProps) => {
  const isCritical = priority === "Critical";

  return (
    <div
      className={`p-4 mb-3 rounded-lg border-l-4 flex items-center gap-4 animate-pulse 
            ${isCritical ? "bg-red-900/20 border-ag-danger text-white" : "bg-ag-card border-ag-warning text-white"}`}
    >
      {isCritical ? (
        <ShieldAlert className="text-ag-danger" size={28} />
      ) : (
        <AlertCircle className="text-ag-warning" size={28} />
      )}

      <div className="flex-1">
        <h4 className="font-bold text-lg uppercase">{type} DETECTED</h4>
        <p className="text-sm opacity-80">
          Camera: {camera_id} | Confidence: {confidence}%
        </p>
      </div>

      <div className="text-xs font-mono bg-black/30 px-2 py-1 rounded">
        {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};

export default AlertCard;
