'use client';

import React, { useState } from 'react';
import { useSettingsStore } from '@/context/SettingsStoreContext';
import { SettingDefinition, SettingsSectionData } from '@/data/settings';
import { MOCK_ADMIN_USER, isSuperAdmin } from '@/lib/auth';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Dialog } from '@/components/ui/Dialog';
import {
  Globe,
  Cpu,
  Layers,
  GitFork,
  FileText,
  Database,
  ShieldCheck,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Server,
  Sparkles,
  Info,
  Check,
  X,
  Sliders,
} from 'lucide-react';

export default function SettingsPage() {
  const {
    sections,
    activeSectionId,
    setActiveSectionId,
    updateSettingValue,
    isDirty,
    unsavedSectionIds,
    saveChanges,
    resetSection,
    resetAllSettings,
    feedbackMessage,
    clearFeedback,
  } = useSettingsStore();

  const activeSection: SettingsSectionData = sections[activeSectionId] || sections.general;

  const [resetModalTarget, setResetModalTarget] = useState<'SECTION' | 'ALL' | null>(null);
  const [saveSuccessToast, setSaveSuccessToast] = useState<string | null>(null);

  const currentUserRole = MOCK_ADMIN_USER.role;
  const userIsSuperAdmin = isSuperAdmin(currentUserRole);

  const handleSaveActiveSection = () => {
    saveChanges(activeSectionId);
    setSaveSuccessToast(`Saved changes for ${activeSection.title}.`);
    setTimeout(() => setSaveSuccessToast(null), 4000);
  };

  const handleConfirmReset = () => {
    if (resetModalTarget === 'SECTION') {
      resetSection(activeSectionId);
    } else if (resetModalTarget === 'ALL') {
      resetAllSettings();
    }
    setResetModalTarget(null);
  };

  const getSectionIcon = (iconName: string) => {
    switch (iconName) {
      case 'Globe':
        return <Globe className="h-4 w-4" />;
      case 'Cpu':
        return <Cpu className="h-4 w-4" />;
      case 'Layers':
        return <Layers className="h-4 w-4" />;
      case 'GitFork':
        return <GitFork className="h-4 w-4" />;
      case 'FileText':
        return <FileText className="h-4 w-4" />;
      case 'Database':
        return <Database className="h-4 w-4" />;
      case 'ShieldCheck':
        return <ShieldCheck className="h-4 w-4" />;
      default:
        return <Globe className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <PageHeader
        title="System Settings"
        subtitle="Configure Juris AI platform behavior and research pipeline preferences."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setResetModalTarget('ALL')}
              className="text-[#526176] hover:text-[#8B2E2E]"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" /> Reset All
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={!isDirty}
              onClick={() => saveChanges()}
            >
              <Save className="h-3.5 w-3.5 mr-1" /> Save Changes
            </Button>
          </div>
        }
      />

      {/* Global Feedback Banner */}
      {(feedbackMessage || saveSuccessToast) && (
        <div className="p-4 rounded-xl bg-[#D0EDDB] border border-[#A1DBB7] text-[#1E6B45] text-xs font-mono flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{saveSuccessToast || feedbackMessage}</span>
          </div>
          <button
            onClick={clearFeedback}
            className="text-[#1E6B45] hover:text-[#14472E] font-bold cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Unsaved Changes Banner */}
      {isDirty && (
        <div className="p-4 rounded-xl bg-[#FBF3D4] border border-[#F3E3A1] text-[#7A5A0F] text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>
              Unsaved changes in <strong>{unsavedSectionIds.length}</strong> section
              {unsavedSectionIds.length > 1 ? 's' : ''} (
              {unsavedSectionIds.map((id) => sections[id]?.title).join(', ')}).
            </span>
          </div>
          <Button variant="primary" size="sm" onClick={() => saveChanges()} className="bg-[#7A5A0F] hover:bg-[#5C430B] text-white">
            <Save className="h-3.5 w-3.5 mr-1" /> Save All Sections
          </Button>
        </div>
      )}

      {/* MOBILE / TABLET HORIZONTAL SECTION TABS */}
      <div className="lg:hidden overflow-x-auto pb-2 flex items-center gap-2 border-b border-[#C9D4E1]">
        {Object.values(sections).map((sec) => {
          const isSelected = sec.id === activeSectionId;
          const hasUnsaved = unsavedSectionIds.includes(sec.id);
          return (
            <button
              key={sec.id}
              onClick={() => setActiveSectionId(sec.id)}
              className={`px-3 py-2 rounded-lg text-xs font-mono font-medium whitespace-nowrap flex items-center gap-2 transition-colors cursor-pointer ${
                isSelected
                  ? 'bg-[#2563A8] text-white shadow-xs'
                  : 'bg-white text-[#526176] hover:bg-[#EFF3F7]'
              }`}
            >
              {getSectionIcon(sec.iconName)}
              <span>{sec.title}</span>
              {hasUnsaved && (
                <span className="h-2 w-2 rounded-full bg-[#B7791F]" />
              )}
            </button>
          );
        })}
      </div>

      {/* MAIN LAYOUT: DESKTOP 2-COLUMN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* DESKTOP NAVIGATION SIDEBAR (4 Cols) */}
        <div className="hidden lg:block lg:col-span-4 space-y-2">
          <div className="p-2 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-1">
            <span className="px-3 py-2 text-[10px] font-mono font-bold text-[#718096] uppercase tracking-wider block">
              Configuration Sections
            </span>
            {Object.values(sections).map((sec) => {
              const isSelected = sec.id === activeSectionId;
              const hasUnsaved = unsavedSectionIds.includes(sec.id);
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveSectionId(sec.id)}
                  className={`w-full px-3 py-2.5 rounded-lg text-xs font-mono text-left flex items-center justify-between transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#2563A8] text-white font-bold shadow-xs'
                      : 'text-[#17253A] hover:bg-[#EFF3F7]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {getSectionIcon(sec.iconName)}
                    <span>{sec.title}</span>
                  </div>
                  {hasUnsaved && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                        isSelected
                          ? 'bg-white text-[#7A5A0F]'
                          : 'bg-[#FBF3D4] text-[#7A5A0F]'
                      }`}
                    >
                      Modified
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Development Info Box */}
          <div className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-2 text-xs font-mono text-[#526176]">
            <div className="flex items-center gap-2 text-[#17253A] font-bold">
              <Server className="h-4 w-4 text-[#2563A8]" />
              <span>Environment Notice</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              These settings represent prototype configuration fields for the eventual GraphRAG pipeline. Updates are maintained in browser session memory.
            </p>
          </div>
        </div>

        {/* SETTINGS CONTENT PANEL (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="p-6 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
            {/* Section Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#D9E1EA] pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-2 rounded-lg bg-[#D9E7F5] text-[#2563A8]">
                    {getSectionIcon(activeSection.iconName)}
                  </span>
                  <h3 className="text-base font-bold text-[#17253A]">{activeSection.title}</h3>
                </div>
                <p className="text-xs text-[#526176] font-mono mt-1">
                  {activeSection.description}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setResetModalTarget('SECTION')}
                  className="text-[#526176] text-xs font-mono"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1" /> Reset Section
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSaveActiveSection}
                  disabled={!unsavedSectionIds.includes(activeSectionId)}
                >
                  <Save className="h-3.5 w-3.5 mr-1" /> Save Section
                </Button>
              </div>
            </div>

            {/* CONNECTION STATUS BANNER FOR LLM & GRAPH */}
            {(activeSectionId === 'ai' || activeSectionId === 'graph') && (
              <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-[#718096]" />
                  <div>
                    <span className="font-bold text-[#17253A]">Backend Service Status: </span>
                    <span className="text-[#526176]">
                      {activeSectionId === 'ai' ? 'LLM Provider API' : 'Neo4j Graph Database'}
                    </span>
                  </div>
                </div>
                <Badge variant="warning">Not Connected (Integration Pending)</Badge>
              </div>
            )}

            {/* DYNAMIC SETTINGS FIELDS FORM */}
            <div className="space-y-6">
              {Object.values(activeSection.settings).map((field: SettingDefinition) => {
                const isRestricted = field.requiresSuperAdmin && !userIsSuperAdmin;

                return (
                  <div
                    key={field.key}
                    className="p-4 rounded-xl bg-[#EFF3F7]/40 border border-[#D9E1EA] space-y-3 transition-colors hover:bg-[#EFF3F7]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <label className="block text-xs font-mono font-bold text-[#17253A]">
                          {field.label}
                        </label>
                        <p className="text-[11px] font-mono text-[#526176] mt-0.5">
                          {field.description}
                        </p>
                      </div>

                      {field.requiresSuperAdmin && (
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          <Lock className="h-3 w-3 mr-1" /> Super Admin
                        </Badge>
                      )}
                    </div>

                    {/* FIELD INPUT CONTROL ACCORDING TO TYPE */}
                    <div className="pt-1">
                      {/* TEXT INPUT */}
                      {field.type === 'text' && (
                        <Input
                          type="text"
                          value={field.value}
                          disabled={isRestricted}
                          onChange={(e) =>
                            updateSettingValue(activeSectionId, field.key, e.target.value)
                          }
                          className="bg-white font-mono text-xs max-w-md"
                        />
                      )}

                      {/* NUMBER INPUT */}
                      {field.type === 'number' && (
                        <div className="flex items-center gap-2 max-w-xs">
                          <Input
                            type="number"
                            value={field.value}
                            min={field.min}
                            max={field.max}
                            step={field.step || 1}
                            disabled={isRestricted}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value);
                              if (!isNaN(val)) {
                                updateSettingValue(activeSectionId, field.key, val);
                              }
                            }}
                            className="bg-white font-mono text-xs"
                          />
                          {field.unit && (
                            <span className="text-xs font-mono text-[#718096]">
                              {field.unit}
                            </span>
                          )}
                        </div>
                      )}

                      {/* SLIDER INPUT */}
                      {field.type === 'slider' && (
                        <div className="space-y-2 max-w-md">
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-[#718096]">Value:</span>
                            <span className="font-bold text-[#2563A8] bg-white px-2 py-0.5 rounded border border-[#C9D4E1]">
                              {field.value}
                            </span>
                          </div>
                          <input
                            type="range"
                            min={field.min}
                            max={field.max}
                            step={field.step || 0.05}
                            value={field.value}
                            disabled={isRestricted}
                            onChange={(e) =>
                              updateSettingValue(
                                activeSectionId,
                                field.key,
                                parseFloat(e.target.value)
                              )
                            }
                            className="w-full h-2 bg-[#D9E1EA] rounded-lg appearance-none cursor-pointer accent-[#2563A8]"
                          />
                          <div className="flex justify-between text-[10px] font-mono text-[#718096]">
                            <span>{field.min}</span>
                            <span>{field.max}</span>
                          </div>
                        </div>
                      )}

                      {/* SELECT DROPDOWN */}
                      {field.type === 'select' && (
                        <Select
                          density="dense"
                          value={field.value}
                          disabled={isRestricted}
                          onChange={(e) =>
                            updateSettingValue(activeSectionId, field.key, e.target.value)
                          }
                          className="bg-white font-mono text-xs max-w-md"
                        >
                          {field.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </Select>
                      )}

                      {/* BOOLEAN SWITCH */}
                      {field.type === 'boolean' && (
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            disabled={isRestricted}
                            onClick={() =>
                              updateSettingValue(activeSectionId, field.key, !field.value)
                            }
                            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                              field.value ? 'bg-[#1E6B45]' : 'bg-[#C9D4E1]'
                            }`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                field.value ? 'translate-x-5' : 'translate-x-0'
                              }`}
                            />
                          </button>
                          <span className="text-xs font-mono font-semibold text-[#17253A]">
                            {field.value ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                      )}

                      {/* MASKED SECRET FIELD */}
                      {field.type === 'masked' && (
                        <div className="space-y-1.5 max-w-md">
                          <Input
                            type="text"
                            value={field.value}
                            disabled={true}
                            className="bg-[#EFF3F7] font-mono text-xs text-[#718096]"
                          />
                          <p className="text-[10px] font-mono text-[#718096] flex items-center gap-1">
                            <Lock className="h-3 w-3 text-[#1E6B45]" />
                            Managed server-side via environment variables. Credentials are never sent to the client.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* CONFIRMATION RESET DIALOG */}
      {resetModalTarget && (
        <Dialog
          isOpen={true}
          onClose={() => setResetModalTarget(null)}
          title={
            resetModalTarget === 'SECTION'
              ? `Reset ${activeSection.title}?`
              : 'Reset All System Settings?'
          }
          description={
            resetModalTarget === 'SECTION'
              ? `Revert all settings in "${activeSection.title}" to default development baseline configurations.`
              : 'Revert all platform sections to default development baseline configurations.'
          }
          footer={
            <>
              <Button variant="ghost" onClick={() => setResetModalTarget(null)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleConfirmReset}>
                <RotateCcw className="h-3.5 w-3.5 mr-1" /> Confirm Reset
              </Button>
            </>
          }
        >
          <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono text-[#526176] space-y-1">
            <span className="font-bold text-[#17253A]">Target Section:</span>
            <p>{resetModalTarget === 'SECTION' ? activeSection.title : 'All 7 Configuration Sections'}</p>
          </div>
        </Dialog>
      )}
    </div>
  );
}
