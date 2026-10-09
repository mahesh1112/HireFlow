import { render, screen, fireEvent } from "@testing-library/react";
import { CandidateCard } from "@/components/cards/CandidateCard";
import type { ScreeningResult } from "@/lib/types";

const mockResult: ScreeningResult = {
  result_id: "result-1",
  resume_id: "resume-1",
  job_id: "job-1",
  rank: 1,
  fit_score: 92,
  status: "EXCELLENT",
  passed_knockouts: true,
  knockout_failures: [],
  category_scores: {
    skills_match: 95,
    experience_relevance: 90,
    career_progression: 85,
    measurable_achievements: 88,
  },
  strengths: ["Strong Python experience", "Recent AWS projects"],
  weaknesses: ["No Kubernetes experience"],
  match_explanation: "Strong technical fit with relevant leadership experience.",
  skills_matched: [
    {
      required_skill: "Python",
      candidate_skill: "Python",
      match_confidence: 0.98,
      years_in_profile: 7,
    },
  ],
  skills_missing: [
    {
      required_skill: "Kubernetes",
      candidate_has: false,
      importance: "high",
    },
  ],
  candidate_name: "John Doe",
  candidate_email: "john@example.com",
  candidate_location: "Bangalore, India",
  total_exp_years: 7,
  is_shortlisted: false,
  created_at: "2026-02-21T10:30:00Z",
  screening_time_ms: 2100,
};

describe("CandidateCard", () => {
  const defaultProps = {
    result: mockResult,
    isSelected: false,
    onToggleSelect: jest.fn(),
    onShortlist: jest.fn(),
    rank: 1,
  };

  it("renders candidate name", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("renders fit score", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText("92")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText(/excellent/i)).toBeInTheDocument();
  });

  it("renders rank", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("calls onToggleSelect when checkbox clicked", () => {
    render(<CandidateCard {...defaultProps} />);
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    expect(defaultProps.onToggleSelect).toHaveBeenCalledWith("result-1");
  });

  it("shows shortlist button when not shortlisted", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText(/shortlist/i)).toBeInTheDocument();
  });

  it("expands details when expand button clicked", () => {
    render(<CandidateCard {...defaultProps} />);
    const expandButton = screen.getByRole("button", { name: "" });
    // Click the last button (expand)
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[buttons.length - 1]);
    expect(screen.getByText("Score Breakdown")).toBeInTheDocument();
  });

  it("shows selected state when isSelected is true", () => {
    render(<CandidateCard {...defaultProps} isSelected={true} />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).toBeChecked();
  });

  it("renders candidate email", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("renders experience years", () => {
    render(<CandidateCard {...defaultProps} />);
    expect(screen.getByText(/7 yrs experience/i)).toBeInTheDocument();
  });
});
