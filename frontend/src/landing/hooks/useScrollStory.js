import { useState, useEffect } from 'react';

export const TIMELINE_STAGES = [
  { id: 'origin', index: '01', label: 'ORIGIN' },
  { id: 'distribution', index: '02', label: 'DISTRIBUTION' },
  { id: 'provenance', index: '03', label: 'PROVENANCE' },
  { id: 'leak', index: '04', label: 'LEAK' },
  { id: 'investigation', index: '05', label: 'INVESTIGATION' },
  { id: 'verification', index: '06', label: 'VERIFICATION' },
  { id: 'source', index: '07', label: 'SOURCE' },
];

export function useScrollStory() {
  const [activeStage, setActiveStage] = useState('01');
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (totalHeight <= 0) return;
      
      const currentScroll = window.scrollY;
      const progress = Math.min(1, Math.max(0, currentScroll / totalHeight));
      setScrollProgress(progress);

      // Determine active stage based on scroll percentage
      if (progress < 0.12) setActiveStage('01');
      else if (progress < 0.26) setActiveStage('02');
      else if (progress < 0.40) setActiveStage('03');
      else if (progress < 0.54) setActiveStage('04');
      else if (progress < 0.70) setActiveStage('05');
      else if (progress < 0.86) setActiveStage('06');
      else setActiveStage('07');
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToStage = (stageId) => {
    const el = document.getElementById(`stage-${stageId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return { activeStage, scrollProgress, scrollToStage };
}
