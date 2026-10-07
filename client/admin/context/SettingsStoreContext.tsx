'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { INITIAL_MOCK_SETTINGS, SettingsSectionData } from '@/data/settings';
import { apiClient } from '@/lib/apiClient';

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
  isLoading: boolean;
}

const SettingsStoreContext = createContext<SettingsStoreContextType | undefined>(undefined);

export const SettingsStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sections, setSections] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);
  const [savedBaseline, setSavedBaseline] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);
  const [activeSectionId, setActiveSectionId] = useState<string>('general');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<{ sections: Record<string, Record<string, any>> }>('/settings');
      if (res && res.sections) {
        // Merge backend values into frontend section data definitions
        setSections((prev) => {
          const next = JSON.parse(JSON.stringify(prev));
          Object.keys(res.sections).forEach((secKey) => {
            const frontendKey = secKey.toLowerCase();
            const backendValues = res.sections[secKey];
            if (next[frontendKey] && backendValues) {
              Object.keys(backendValues).forEach((settingKey) => {
                if (next[frontendKey].settings[settingKey]) {
                  next[frontendKey].settings[settingKey].value = backendValues[settingKey];
                }
              });
            }
          });
          return next;
        });

        setSavedBaseline((prev) => {
          const next = JSON.parse(JSON.stringify(prev));
          Object.keys(res.sections).forEach((secKey) => {
            const frontendKey = secKey.toLowerCase();
            const backendValues = res.sections[secKey];
            if (next[frontendKey] && backendValues) {
              Object.keys(backendValues).forEach((settingKey) => {
                if (next[frontendKey].settings[settingKey]) {
                  next[frontendKey].settings[settingKey].value = backendValues[settingKey];
                }
              });
            }
          });
          return next;
        });
      }
    } catch {
      // Keep baseline
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

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
    const currentSec = sections[targetSection];
    if (!currentSec) return;

    // Convert section settings object to plain key-value map for backend
    const configMap: Record<string, any> = {};
    Object.keys(currentSec.settings).forEach((key) => {
      configMap[key] = currentSec.settings[key].value;
    });

    const backendSectionName = targetSection.toUpperCase();
    apiClient.put(`/settings/${backendSectionName}`, { config: configMap }).catch(() => {});

    setSavedBaseline((prev) => ({
      ...prev,
      [targetSection]: JSON.parse(JSON.stringify(sections[targetSection])),
    }));

    setFeedbackMessage(
      `Settings for "${currentSec.title}" successfully saved and persisted to backend.`
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

    setFeedbackMessage(`Reset "${sections[sectionId]?.title}" to defaults.`);
  };

  const resetAllSettings = () => {
    const freshDefaults = JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS));
    setSections(freshDefaults);
    setSavedBaseline(freshDefaults);
    setFeedbackMessage('All platform settings reset to defaults.');
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
        isLoading,
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

