"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ── Category definitions ─────────────────────────────────────────────────────
const CATEGORIES = [
  {
    key: "culture",
    label: "Culture & History",
    icon: "🏛️",
    description: "Forts, museums, temples, heritage walks",
    gradient: "from-amber-500/20 to-orange-500/20",
    border: "border-amber-500/30",
    accent: "text-amber-300",
    fill: "bg-gradient-to-r from-amber-500 to-orange-400",
  },
  {
    key: "food",
    label: "Food & Dining",
    icon: "🍜",
    description: "Street food, fine dining, culinary tours",
    gradient: "from-red-500/20 to-rose-500/20",
    border: "border-red-500/30",
    accent: "text-red-300",
    fill: "bg-gradient-to-r from-red-500 to-rose-400",
  },
  {
    key: "adventure",
    label: "Adventure",
    icon: "🏔️",
    description: "Trekking, rafting, extreme sports",
    gradient: "from-emerald-500/20 to-green-500/20",
    border: "border-emerald-500/30",
    accent: "text-emerald-300",
    fill: "bg-gradient-to-r from-emerald-500 to-green-400",
  },
  {
    key: "shopping",
    label: "Shopping",
    icon: "🛍️",
    description: "Local markets, malls, souvenir shops",
    gradient: "from-pink-500/20 to-fuchsia-500/20",
    border: "border-pink-500/30",
    accent: "text-pink-300",
    fill: "bg-gradient-to-r from-pink-500 to-fuchsia-400",
  },
  {
    key: "nature",
    label: "Nature & Relaxation",
    icon: "🌿",
    description: "Parks, gardens, scenic viewpoints, spas",
    gradient: "from-teal-500/20 to-cyan-500/20",
    border: "border-teal-500/30",
    accent: "text-teal-300",
    fill: "bg-gradient-to-r from-teal-500 to-cyan-400",
  },
  {
    key: "nightlife",
    label: "Nightlife",
    icon: "🌙",
    description: "Bars, clubs, live music, night markets",
    gradient: "from-violet-500/20 to-purple-500/20",
    border: "border-violet-500/30",
    accent: "text-violet-300",
    fill: "bg-gradient-to-r from-violet-500 to-purple-400",
  },
];

// ── Types ────────────────────────────────────────────────────────────────────
interface PreferencePollProps {
  onSubmit: (weights: Record<string, number>) => void;
  onSkip: () => void;
}

// ── Dot rating selector ──────────────────────────────────────────────────────
const DotRating = ({
  value,
  onChange,
  fillClass,
}: {
  value: number;
  onChange: (v: number) => void;
  fillClass: string;
}) => (
  <div className="flex items-center gap-1.5">
    {[1, 2, 3, 4, 5].map((dot) => (
      <motion.button
        key={dot}
        type="button"
        onClick={() => onChange(dot)}
        whileHover={{ scale: 1.3 }}
        whileTap={{ scale: 0.9 }}
        className={`w-5 h-5 rounded-full transition-all duration-200 border-2 ${
          dot <= value
            ? `${fillClass} border-transparent shadow-md`
            : "bg-zinc-800/60 border-zinc-600/40 hover:border-zinc-500/60"
        }`}
        aria-label={`Rate ${dot} out of 5`}
      />
    ))}
    <span className="ml-2 text-xs font-bold text-zinc-400 tabular-nums w-8">
      {value}/5
    </span>
  </div>
);

// ── Main component ───────────────────────────────────────────────────────────
export default function PreferencePoll({ onSubmit, onSkip }: PreferencePollProps) {
  const [weights, setWeights] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    CATEGORIES.forEach((c) => (initial[c.key] = 3));
    return initial;
  });

  const [isVisible, setIsVisible] = useState(true);

  const handleSubmit = () => {
    setIsVisible(false);
    // Small delay so exit animation plays
    setTimeout(() => onSubmit(weights), 400);
  };

  const handleSkip = () => {
    setIsVisible(false);
    setTimeout(() => onSkip(), 400);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className="w-full max-w-2xl mx-auto mb-8"
        >
          <div className="p-6 rounded-3xl bg-gradient-to-br from-zinc-900/90 via-zinc-900/80 to-zinc-800/90 border border-violet-500/25 backdrop-blur-2xl shadow-2xl shadow-violet-500/5">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                className="p-3 bg-violet-500/15 rounded-2xl"
              >
                <span className="text-3xl">⚖️</span>
              </motion.div>
              <div>
                <h3 className="text-xl font-bold bg-gradient-to-r from-violet-300 to-fuchsia-300 bg-clip-text text-transparent">
                  What matters most to you?
                </h3>
                <p className="text-sm text-zinc-400 mt-0.5">
                  Rate each category to personalize your itinerary
                </p>
              </div>
            </div>

            {/* Category grid */}
            <div className="space-y-3 mb-6">
              {CATEGORIES.map((cat, idx) => (
                <motion.div
                  key={cat.key}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.07 }}
                  whileHover={{ x: 4 }}
                  className={`flex items-center justify-between p-4 rounded-2xl bg-gradient-to-br ${cat.gradient} border ${cat.border} backdrop-blur-xl`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-2xl flex-shrink-0">{cat.icon}</span>
                    <div className="min-w-0">
                      <p className={`font-semibold text-sm ${cat.accent}`}>
                        {cat.label}
                      </p>
                      <p className="text-xs text-zinc-400 truncate">
                        {cat.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex-shrink-0 ml-3">
                    <DotRating
                      value={weights[cat.key]}
                      onChange={(v) =>
                        setWeights((prev) => ({ ...prev, [cat.key]: v }))
                      }
                      fillClass={cat.fill}
                    />
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleSkip}
                className="px-5 py-2.5 text-sm text-zinc-400 hover:text-zinc-200 transition-colors rounded-xl hover:bg-zinc-800/50"
              >
                Skip — use defaults
              </button>
              <motion.button
                type="button"
                onClick={handleSubmit}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="px-8 py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white rounded-2xl font-bold shadow-lg shadow-violet-500/30 hover:shadow-violet-500/50 transition-all text-sm"
              >
                Apply Preferences ✨
              </motion.button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
