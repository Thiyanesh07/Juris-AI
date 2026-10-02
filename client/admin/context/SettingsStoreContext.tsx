'use client';

import React, { createContext, useContext, useState, useMemo } from 'react';
import { INITIAL_MOCK_SETTINGS, SettingsSectionData, SettingDefinition } from '@/data/settings';

interface SettingsStoreContextType {
  sections: Record<string, SettingsSectionData>;
  activeSectionId: string;
  setActiveSectionId: (id: string) => void;
  updateSettingValue: (sectionId: string, key: string, value: any) => void;
  isDirty: boolean;
  unsavedSectionIds: string[];
  saveChanges: (sectionId?: string) => void;
  resetSection: (sectionId: string) => void;
  resetAllSettings: () => void;
  savedBaseline: Record<string, SettingsSectionData>;
  feedbackMessage: string | null;
  clearFeedback: () => void;
}

const SettingsStoreContext = createContext<SettingsStoreContextType | undefined>(undefined);

export const SettingsStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Current working state (editable in session)
  const [sections, setSections] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);
  
  // Saved baseline (represents persisted mock settings state)
  const [savedBaseline, setSavedBaseline] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);

  const [activeSectionId, setActiveSectionId] = useState<string>('general');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const updateSettingValue = (sectionId: string, key: string, value: any) => {
    setSections((prev) => {
      const section = prev[sectionId];
      if (!section || !section.settings[key]) return prev;

      return {
        ...prev,
        [sectionId]: {
          ...section,
          settings: {
            ...section.settings,
            [key]: {
              ...section.settings[key],
              value,
            },
          },
        },
      };
    });
  };

  // Compute unsaved sections & overall isDirty
  const unsavedSectionIds = useMemo(() => {
    const dirtyIds: string[] = [];

    Object.keys(sections).forEach((sectionId) => {
      const currentSec = sections[sectionId];
      const savedSec = savedBaseline[sectionId];
      if (!currentSec || !savedSec) return;

      const keys = Object.keys(currentSec.settings);
      const sectionHasChanges = keys.some(
        (key) => JSON.stringify(currentSec.settings[key]?.value) !== JSON.stringify(savedSec.settings[key]?.value)
      );

      if (sectionHasChanges) {
        dirtyIds.push(sectionId);
      }
    });

    return dirtyIds;
  }, [sections, savedBaseline]);

  const isDirty = unsavedSectionIds.length > 0;

  const saveChanges = (sectionId?: string) => {
    const targetSection = sectionId || activeSectionId;
    
    setSavedBaseline((prev) => ({
      ...prev,
      [targetSection]: JSON.parse(JSON.stringify(sections[targetSection])),
    }));

    setFeedbackMessage(
      `Settings for "${sections[targetSection]?.title || 'section'}" updated in development session.`
    );
  };

  const resetSection = (sectionId: string) => {
    setSections((prev) => {
      const defaultSec = INITIAL_MOCK_SETTINGS[sectionId];
      if (!defaultSec) return prev;
      return {
        ...prev,
        [sectionId]: JSON.parse(JSON.stringify(defaultSec)),
      };
    });

    setSavedBaseline((prev) => {
      const defaultSec = INITIAL_MOCK_SETTINGS[sectionId];
      if (!defaultSec) return prev;
      return {
        ...prev,
        [sectionId]: JSON.parse(JSON.stringify(defaultSec)),
      };
    });

    setFeedbackMessage(`Reset "${sections[sectionId]?.title}" to development defaults.`);
  };

  const resetAllSettings = () => {
    const freshDefaults = JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS));
    setSections(freshDefaults);
    setSavedBaseline(freshDefaults);
    setFeedbackMessage('All platform settings reset to development baseline defaults.');
  };

  const clearFeedback = () => setFeedbackMessage(null);

  return (
    <SettingsStoreContext.Provider
      value={{
        sections,
        activeSectionId,
        setActiveSectionId,
        updateSettingValue,
        isDirty,
        unsavedSectionIds,
        saveChanges,
        resetSection,
        resetAllSettings,
        savedBaseline,
        feedbackMessage,
        clearFeedback,
      }}
    >
      {children}
    </SettingsStoreContext.Provider>
  );
};

export const useSettingsStore = () => {
  const context = useContext(SettingsStoreContext);
  if (!context) {
    throw new Error('useSettingsStore must be used within a SettingsStoreProvider');
  }
  return context;
};
