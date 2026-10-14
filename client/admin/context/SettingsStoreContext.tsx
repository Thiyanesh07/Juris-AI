'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import {
  INITIAL_MOCK_SETTINGS,
  SettingsSectionData,
  FRONTEND_TO_BACKEND_SECTION_MAP,
  buildBackendConfigPayload,
  hydrateSectionsFromBackend,
} from '@/data/settings';
import { apiClient } from '@/lib/apiClient';

interface SettingsStoreContextType {
  sections: Record<string, SettingsSectionData>;
  activeSectionId: string;
  setActiveSectionId: (id: string) => void;
  updateSettingValue: (sectionId: string, key: string, value: any) => void;
  isDirty: boolean;
  unsavedSectionIds: string[];
  saveChanges: (sectionId?: string) => Promise<boolean>;
  resetSection: (sectionId: string) => void;
  resetAllSettings: () => void;
  savedBaseline: Record<string, SettingsSectionData>;
  feedbackMessage: string | null;
  errorMessage: string | null;
  clearFeedback: () => void;
  isLoading: boolean;
  isSaving: boolean;
  fetchSettings: () => Promise<void>;
}

const SettingsStoreContext = createContext<SettingsStoreContextType | undefined>(undefined);

export const SettingsStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sections, setSections] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);
  const [savedBaseline, setSavedBaseline] = useState<Record<string, SettingsSectionData>>(INITIAL_MOCK_SETTINGS);
  const [activeSectionId, setActiveSectionId] = useState<string>('general');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.get<{ sections: Record<string, Record<string, any>> }>('/settings');
      if (res && res.sections) {
        setSections((prev) => hydrateSectionsFromBackend(prev, res.sections));
        setSavedBaseline((prev) => hydrateSectionsFromBackend(prev, res.sections));
      }
    } catch (err: any) {
      setErrorMessage(`Failed to load system settings from server: ${err?.message || 'Server unreachable'}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    apiClient
      .get<{ sections: Record<string, Record<string, any>> }>('/settings')
      .then((res) => {
        if (!active) return;
        if (res && res.sections) {
          setSections((prev) => hydrateSectionsFromBackend(prev, res.sections));
          setSavedBaseline((prev) => hydrateSectionsFromBackend(prev, res.sections));
        }
      })
      .catch((err: any) => {
        if (!active) return;
        setErrorMessage(`Failed to load system settings from server: ${err?.message || 'Server unreachable'}`);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

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

  const saveChanges = async (sectionId?: string): Promise<boolean> => {
    const targets = sectionId ? [sectionId] : (unsavedSectionIds.length > 0 ? unsavedSectionIds : [activeSectionId]);
    setIsSaving(true);
    setErrorMessage(null);
    let allSucceeded = true;
    const succeededSections: string[] = [];
    const failedSections: string[] = [];

    for (const targetSection of targets) {
      const currentSec = sections[targetSection];
      if (!currentSec) continue;

      const backendSectionName = FRONTEND_TO_BACKEND_SECTION_MAP[targetSection] || targetSection.toUpperCase();
      const configMap = buildBackendConfigPayload(targetSection, currentSec);

      try {
        const res = await apiClient.put<{ section: string; config: Record<string, any> }>(
          `/settings/${backendSectionName}`,
          { config: configMap }
        );

        if (!res || !res.section) {
          throw new Error('Server returned an empty or invalid response');
        }

        // Commit saved baseline only on server confirmation
        setSavedBaseline((prev) => ({
          ...prev,
          [targetSection]: JSON.parse(JSON.stringify(sections[targetSection])),
        }));
        succeededSections.push(currentSec.title);
      } catch (err: any) {
        allSucceeded = false;
        const msg = err?.message || 'Server save rejected';
        failedSections.push(`${currentSec.title} (${msg})`);
      }
    }

    if (failedSections.length > 0) {
      setErrorMessage(`Failed to save settings for: ${failedSections.join(', ')}`);
    } else if (succeededSections.length > 0) {
      setFeedbackMessage(
        `Settings for ${succeededSections.join(', ')} successfully saved and persisted to backend.`
      );
    }

    setIsSaving(false);
    return allSucceeded;
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

  const clearFeedback = () => {
    setFeedbackMessage(null);
    setErrorMessage(null);
  };

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
        errorMessage,
        clearFeedback,
        isLoading,
        isSaving,
        fetchSettings,
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

