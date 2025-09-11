import EmotionMonitor from "@/components/EmotionMonitor";
import AuthGuard from "@/components/AuthGuard";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Emotion Monitor</h1>
        <EmotionMonitor />
      </div>
    </AuthGuard>
  );
}


