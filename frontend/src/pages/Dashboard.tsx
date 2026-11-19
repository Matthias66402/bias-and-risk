import { useNavigate, useParams } from "react-router-dom";
import { PhaseIntro } from "../components/ui";
import { PHASES, type PhaseKey } from "../phases";
import DataTab from "./dashboard/DataTab";
import DeploymentTab from "./dashboard/DeploymentTab";
import FeedbackTab from "./dashboard/FeedbackTab";
import LabelingTab from "./dashboard/LabelingTab";
import ModelTab from "./dashboard/ModelTab";
import ProblemTab from "./dashboard/ProblemTab";

const TABS: Record<PhaseKey, () => React.JSX.Element> = {
  problem: ProblemTab, data: DataTab, labeling: LabelingTab, model: ModelTab, deployment: DeploymentTab, feedback: FeedbackTab,
};

export default function Dashboard() {
  const { phase = "problem" } = useParams();
  const nav = useNavigate();
  const key = (phase in TABS ? phase : "problem") as PhaseKey;
  const Tab = TABS[key];
  return (
    <div className="stack">
      <div className="tabs">
        {PHASES.map((p, i) => (
          <button key={p.key} className={p.key === key ? "on" : ""} onClick={() => nav(`/dashboard/${p.key}`)}>
            {i + 1}. {p.title}
          </button>
        ))}
      </div>
      <PhaseIntro phase={key} />
      <Tab />
    </div>
  );
}
