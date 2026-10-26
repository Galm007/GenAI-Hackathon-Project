"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  PenTool,
  Target,
  UserCheck,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Sparkles,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import { createEvaluation, ApiError, type IntakeFormData } from "@/lib/api";
import { PdfDropzone } from "./PdfDropzone";
import { SchoolPicker } from "./SchoolPicker";
import { ContextStep } from "./ContextStep";
import { Button } from "@/components/ui/button";
import { countWords } from "@/lib/format";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 1, label: "Upload", icon: FileText, desc: "Transcript & resume" },
  { id: 2, label: "Writing", icon: PenTool, desc: "Activities & essay" },
  { id: 3, label: "Targets", icon: Target, desc: "Institutions & major" },
  { id: 4, label: "Context", icon: UserCheck, desc: "Background & consent" },
] as const;

export function IntakeWizard() {
  const router = useRouter();
  const [step, setStep] = React.useState<number>(1);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Files state
  const [transcriptFile, setTranscriptFile] = React.useState<File | undefined>();
  const [resumeFile, setResumeFile] = React.useState<File | undefined>();

  // Form state
  const [intendedMajor, setIntendedMajor] = React.useState("");
  const [targetSchools, setTargetSchools] = React.useState<string[]>(["uiuc"]);
  const [earlyRounds, setEarlyRounds] = React.useState<Record<string, string>>({
    uiuc: "EA",
  });
  const [applicationDeadline, setApplicationDeadline] = React.useState<string>("");

  const [activitiesText, setActivitiesText] = React.useState("");
  const [resumeText, setResumeText] = React.useState("");
  const [essayText, setEssayText] = React.useState("");
  const [recommendationText, setRecommendationText] = React.useState("");

  const [residencyState, setResidencyState] = React.useState("IL");
  const [schoolType, setSchoolType] = React.useState("Public");
  const [firstGen, setFirstGen] = React.useState(false);
  const [lowIncome, setLowIncome] = React.useState(false);
  const [hooks, setHooks] = React.useState<string[]>([]);
  const [consent, setConsent] = React.useState(false);

  const essayWordCount = React.useMemo(() => countWords(essayText), [essayText]);

  const handleToggleHook = (hook: string) => {
    setHooks((prev) =>
      prev.includes(hook) ? prev.filter((h) => h !== hook) : [...prev, hook]
    );
  };

  const handleLoadMayaDemo = () => {
    setIntendedMajor("Computer Science");
    setTargetSchools(["uiuc"]);
    setEarlyRounds({ uiuc: "EA" });
    setActivitiesText(
      `1. Competitive programming — Team captain, School CS club (Grades 10, 11, 12; 6 hrs/wk, 40 wks/yr). USACO Gold; leads weekly practice for 14 members; 3rd at regional high school ICPC.
2. Crop-disease classifier — Independent researcher (Grades 11, 12; 8 hrs/wk, 25 wks/yr). Trained a small CNN on leaf images; presented at regional science fair.
3. Math Honor Society — Peer tutor (Grades 11, 12; 3 hrs/wk, 30 wks/yr). Tutored AP Calculus BC and Algebra II students.
4. Varsity Track & Field — Distance runner (Grades 9, 10, 11, 12; 10 hrs/wk, 20 wks/yr). 1600m and 3200m varsity runner.`
    );
    setEssayText(
      `The glow of the terminal at 2 a.m. has become my comfort zone. It started with a simple bug in my competitive programming solution—an off-by-one error in a segment tree that cost our team a spot in the finals. Most people would have gone to sleep, but I couldn't let it rest. Debugging isn't just about finding where code fails; it's about understanding how systems think. When I applied this curiosity to plant pathology, training a convolutional neural network to detect fungal infections on corn leaves, I realized algorithms don't just solve puzzles on a screen. They solve tangible crises for farmers in our community who lose entire harvests to preventable blight. Standing in the field with local growers, showing them how a snapshot on a phone could diagnose a leaf in seconds, bridged the gap between abstract computer science and human impact. That intersection is where I intend to spend my life.`
    );
    setResidencyState("IL");
    setSchoolType("Public");
    setFirstGen(false);
    setLowIncome(false);
    setHooks([]);
    setConsent(true);
    toast.success("Loaded Maya's demo profile (UIUC CS applicant)!");
  };

  const handleNext = () => {
    if (step === 1) {
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    } else if (step === 3) {
      if (!intendedMajor.trim()) {
        toast.error("Please enter your intended major.");
        return;
      }
      if (targetSchools.length === 0) {
        toast.error("Please select at least one target institution.");
        return;
      }
      setStep(4);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async () => {
    // 1. Validate files / activities
    const hasDossier =
      Boolean(transcriptFile) ||
      Boolean(activitiesText.trim()) ||
      Boolean(resumeFile) ||
      Boolean(resumeText.trim());

    if (!hasDossier) {
      toast.error("Upload a transcript or paste an activities list.");
      setStep(1);
      return;
    }

    // 2. Validate major
    if (!intendedMajor.trim()) {
      toast.error("Please specify your intended major.");
      setStep(3);
      return;
    }

    // 3. Validate target schools
    if (targetSchools.length === 0) {
      toast.error("Please select at least one target school.");
      setStep(3);
      return;
    }

    // 4. Validate consent
    if (!consent) {
      toast.error("Please agree to the consent checkbox to continue.");
      return;
    }

    setIsSubmitting(true);

    const formData: IntakeFormData = {
      intended_major: intendedMajor.trim(),
      target_schools: targetSchools,
      early_round: earlyRounds,
      activities_text: activitiesText.trim() || undefined,
      resume_text: resumeText.trim() || undefined,
      essay_text: essayText.trim() || undefined,
      recommendation_text: recommendationText.trim() || undefined,
      hooks,
      context: {
        residency_state: residencyState || undefined,
        country: "US",
        school_type: schoolType || undefined,
        first_gen: firstGen,
        low_income: lowIncome,
      },
      application_deadline: applicationDeadline || undefined,
    };

    try {
      const res = await createEvaluation(formData, {
        transcript: transcriptFile,
        resume: resumeFile,
      });

      toast.success("Dossier received! Convening admissions committee...");
      router.push(`/room/${res.run_id}`);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 413) {
          toast.error("File exceeds 10 MB. Please upload a smaller PDF.");
        } else if (err.status === 415) {
          toast.error("Invalid file format. Please upload a valid PDF.");
        } else if (err.status === 429) {
          toast.error("Rate limit reached.", {
            description: "Live committee capacity is full. Would you like to replay Maya's demo evaluation?",
            action: {
              label: "Replay Maya Demo",
              onClick: () => router.push("/room/demo/maya-uiuc"),
            },
          });
        } else {
          toast.error(err.message || "Failed to create evaluation run.");
        }
      } else if (err instanceof Error) {
        toast.error(err.message || "An unexpected error occurred.");
      } else {
        toast.error("Failed to connect to AdCom API.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-3xl rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-6 sm:p-8 shadow-2xl">
      {/* Quick Replay Banner */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/60 px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
          <Sparkles className="h-4 w-4 text-[var(--color-advocate)]" />
          <span>Want to explore without uploading?</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLoadMayaDemo}
            className="h-7 text-xs text-[var(--color-advocate)] hover:bg-[var(--color-advocate)]/10"
          >
            Pre-fill Maya&apos;s data
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/room/demo/maya-uiuc")}
            className="h-7 gap-1 text-xs border-[var(--color-line)] hover:border-[var(--color-advocate)]"
          >
            <Play className="h-3 w-3 text-[var(--color-admit)]" />
            <span>Launch Live Demo Replay</span>
          </Button>
        </div>
      </div>

      {/* Stepper Header */}
      <div className="mb-8">
        <div className="grid grid-cols-4 gap-2">
          {STEPS.map((s) => {
            const Icon = s.icon;
            const isCurrent = step === s.id;
            const isPassed = step > s.id;

            return (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  if (s.id < step) setStep(s.id);
                }}
                disabled={s.id > step}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-xl p-2.5 text-center transition-colors",
                  isCurrent && "bg-[var(--color-panel-2)] text-[var(--color-advocate)]",
                  isPassed && "text-[var(--color-ink)] hover:bg-[var(--color-panel-2)]/50 cursor-pointer",
                  !isCurrent && !isPassed && "text-[var(--color-muted)] opacity-50 cursor-not-allowed"
                )}
              >
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-mono font-bold transition-transform",
                    isCurrent && "bg-[var(--color-advocate)] text-white scale-105 shadow-md",
                    isPassed && "bg-[var(--color-admit)]/20 text-[var(--color-admit)]",
                    !isCurrent && !isPassed && "bg-[var(--color-line)] text-[var(--color-muted)]"
                  )}
                >
                  {isPassed ? "✓" : s.id}
                </div>
                <span className="text-xs font-medium">{s.label}</span>
                <span className="hidden sm:inline-block text-[10px] text-[var(--color-muted)] font-mono">
                  {s.desc}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[320px]">
        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-ink)]">
                1. Upload Dossier Files
              </h2>
              <p className="text-xs text-[var(--color-muted)] mt-1">
                Upload your unofficial or official high school transcript (PDF). We parse course grades, AP/IB scores, and rigor levels.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-[var(--color-muted)] mb-1.5">
                  Academic Transcript (Recommended)
                </label>
                <PdfDropzone
                  label="transcript"
                  file={transcriptFile}
                  onFile={setTranscriptFile}
                  onRemove={() => setTranscriptFile(undefined)}
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[var(--color-muted)] mb-1.5">
                  Student Resume / CV (Optional)
                </label>
                <PdfDropzone
                  label="resume"
                  file={resumeFile}
                  onFile={setResumeFile}
                  onRemove={() => setResumeFile(undefined)}
                />
              </div>
            </div>

            <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)]/40 p-3.5 text-xs text-[var(--color-muted)]">
              <p>
                <strong>No PDF handy?</strong> You can proceed to Step 2 and paste your extracurricular activities, coursework, and personal statement as plain text.
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Writing */}
        {step === 2 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-ink)]">
                2. Activities & Writing Materials
              </h2>
              <p className="text-xs text-[var(--color-muted)] mt-1">
                Paste your extracurricular list and personal statement from the Common App or Coalition application.
              </p>
            </div>

            {/* Activities Textarea */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-mono text-[var(--color-muted)]">
                  Extracurricular Activities & Leadership
                </label>
                <span className="text-[11px] text-[var(--color-muted)] font-mono">
                  Common App 10 activities format
                </span>
              </div>
              <textarea
                value={activitiesText}
                onChange={(e) => setActivitiesText(e.target.value)}
                placeholder="1. Robotics Club — Captain (10 hrs/wk, 36 wks/yr). Led CAD design for state championship team...&#10;2. Varsity Track & Field — Team Captain (8 hrs/wk)..."
                rows={5}
                aria-label="Extracurricular Activities"
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3 text-sm text-[var(--color-ink)] placeholder:text-[var(--color-muted)]/60 focus:border-[var(--color-advocate)] focus:outline-none"
              />
            </div>

            {/* Essay Textarea */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-mono text-[var(--color-muted)]">
                  Personal Statement / Common App Essay
                </label>
                <span
                  className={cn(
                    "text-[11px] font-mono",
                    essayWordCount > 650
                      ? "text-[var(--color-deny)] font-semibold"
                      : "text-[var(--color-muted)]"
                  )}
                >
                  {essayWordCount} / 650 words
                </span>
              </div>
              <textarea
                value={essayText}
                onChange={(e) => setEssayText(e.target.value)}
                placeholder="Paste your main admissions personal essay here..."
                rows={5}
                aria-label="Personal Statement Essay"
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3 text-sm text-[var(--color-ink)] placeholder:text-[var(--color-muted)]/60 focus:border-[var(--color-advocate)] focus:outline-none"
              />
            </div>

            {/* Recommendation Letter (Optional) */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-mono text-[var(--color-muted)]">
                  Counselor or Teacher Recommendation (Optional)
                </label>
                <span className="text-[11px] text-[var(--color-advocate)] font-mono">
                  Unlocks Personal rating 1
                </span>
              </div>
              <textarea
                value={recommendationText}
                onChange={(e) => setRecommendationText(e.target.value)}
                placeholder="Excerpts or full recommendation letter..."
                rows={3}
                aria-label="Recommendation Letter"
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3 text-sm text-[var(--color-ink)] placeholder:text-[var(--color-muted)]/60 focus:border-[var(--color-advocate)] focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Step 3: Targets */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-ink)]">
                3. Intended Major & Target Schools
              </h2>
              <p className="text-xs text-[var(--color-muted)] mt-1">
                Select your intended major and up to 8 institutions for committee evaluation.
              </p>
            </div>

            {/* Intended Major */}
            <div>
              <label className="block text-xs font-mono text-[var(--color-muted)] mb-1.5">
                Intended Major / Academic Focus *
              </label>
              <input
                type="text"
                value={intendedMajor}
                onChange={(e) => setIntendedMajor(e.target.value)}
                placeholder="e.g. Computer Science, Mechanical Engineering, Economics..."
                aria-label="Intended Major"
                className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-2 text-sm text-[var(--color-ink)] placeholder:text-[var(--color-muted)]/60 focus:border-[var(--color-advocate)] focus:outline-none"
              />

              {/* Major quick chips */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-mono text-[var(--color-muted)]">Popular:</span>
                {[
                  "Computer Science",
                  "Electrical Engineering",
                  "Mechanical Engineering",
                  "Economics",
                  "Biology / Pre-Med",
                  "Business Administration",
                ].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setIntendedMajor(m)}
                    className="rounded-full border border-[var(--color-line)] bg-[var(--color-panel-2)]/60 px-2 py-0.5 text-[11px] text-[var(--color-ink)] hover:border-[var(--color-advocate)] hover:text-[var(--color-advocate)] transition-colors"
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* SchoolPicker */}
            <div className="pt-2 border-t border-[var(--color-line)]">
              <SchoolPicker
                selectedSchools={targetSchools}
                earlyRounds={earlyRounds}
                onSelectSchool={(slug) => setTargetSchools((prev) => [...prev, slug])}
                onRemoveSchool={(slug) => {
                  setTargetSchools((prev) => prev.filter((s) => s !== slug));
                  setEarlyRounds((prev) => {
                    const next = { ...prev };
                    delete next[slug];
                    return next;
                  });
                }}
                onSetRound={(slug, round) =>
                  setEarlyRounds((prev) => ({ ...prev, [slug]: round }))
                }
                applicationDeadline={applicationDeadline}
                onSetDeadline={setApplicationDeadline}
              />
            </div>
          </div>
        )}

        {/* Step 4: Context & Consent */}
        {step === 4 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-ink)]">
                4. Applicant Context & Consent
              </h2>
              <p className="text-xs text-[var(--color-muted)] mt-1">
                Provide school context and affirm consent to convene the live committee.
              </p>
            </div>

            <ContextStep
              residencyState={residencyState}
              onSetResidencyState={setResidencyState}
              schoolType={schoolType}
              onSetSchoolType={setSchoolType}
              firstGen={firstGen}
              onSetFirstGen={setFirstGen}
              lowIncome={lowIncome}
              onSetLowIncome={setLowIncome}
              hooks={hooks}
              onToggleHook={handleToggleHook}
              consent={consent}
              onSetConsent={setConsent}
              onLoadMayaDemo={handleLoadMayaDemo}
            />
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="mt-8 flex items-center justify-between border-t border-[var(--color-line)] pt-5">
        <div>
          {step > 1 ? (
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              disabled={isSubmitting}
              className="gap-2 text-xs"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </Button>
          ) : (
            <div />
          )}
        </div>

        <div>
          {step < 4 ? (
            <Button
              type="button"
              onClick={handleNext}
              className="gap-2 text-xs font-semibold"
            >
              Next <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !consent}
              className="gap-2 text-xs font-semibold bg-[var(--color-admit)] hover:bg-[var(--color-admit)]/90 text-white shadow-lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Convening Committee...
                </>
              ) : (
                <>
                  Convene Committee <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
