import { FormEvent } from "react";

type SettingsDialogProps = {
  libraryPath: string;
  provider: string;
  baseUrl: string;
  model: string;
  proxyUrl: string;
  apiKey: string;
  outboundContextPolicy: string;
  apiKeyConfigured: boolean;
  onLibraryPathChange: (value: string) => void;
  onProviderChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onProxyUrlChange: (value: string) => void;
  onApiKeyChange: (value: string) => void;
  onOutboundContextPolicyChange: (value: string) => void;
  onSelectLibrary: (event: FormEvent<HTMLFormElement>) => void;
  onSaveSettings: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
};

export function SettingsDialog({
  libraryPath,
  provider,
  baseUrl,
  model,
  proxyUrl,
  apiKey,
  outboundContextPolicy,
  apiKeyConfigured,
  onLibraryPathChange,
  onProviderChange,
  onBaseUrlChange,
  onModelChange,
  onProxyUrlChange,
  onApiKeyChange,
  onOutboundContextPolicyChange,
  onSelectLibrary,
  onSaveSettings,
  onClose,
}: SettingsDialogProps) {
  return (
    <div className="modal-backdrop">
      <section aria-label="Settings" aria-modal="true" className="modal-panel" role="dialog">
        <header className="modal-header">
          <div>
            <h2>Settings</h2>
            <p>Configure the local library and model provider.</p>
          </div>
          <button aria-label="Close settings dialog" type="button" onClick={onClose}>
            Close
          </button>
        </header>

        <form className="dialog-form settings-section" onSubmit={onSelectLibrary}>
          <h3>Library</h3>
          <label htmlFor="library-path">Library location</label>
          <div className="compact-row">
            <input
              id="library-path"
              placeholder="F:\\KnowledgeAgentLibrary"
              value={libraryPath}
              onChange={(event) => onLibraryPathChange(event.target.value)}
            />
            <button disabled={libraryPath.trim().length === 0} type="submit">
              Select library
            </button>
          </div>
        </form>

        <form className="dialog-form settings-section" onSubmit={onSaveSettings}>
          <h3>Model provider</h3>
          <p className="context-status">{apiKeyConfigured ? "API key configured" : "API key not configured"}</p>

          <label htmlFor="provider">Provider</label>
          <select id="provider" value={provider} onChange={(event) => onProviderChange(event.target.value)}>
            <option value="none">None</option>
            <option value="openai_compatible">OpenAI-compatible</option>
            <option value="ollama">Ollama</option>
          </select>

          <label htmlFor="base-url">Base URL</label>
          <input
            id="base-url"
            placeholder="https://api.example.com/v1"
            value={baseUrl}
            onChange={(event) => onBaseUrlChange(event.target.value)}
          />

          <label htmlFor="proxy-url">Proxy URL</label>
          <input
            id="proxy-url"
            placeholder="http://127.0.0.1:7897"
            value={proxyUrl}
            onChange={(event) => onProxyUrlChange(event.target.value)}
          />

          <label htmlFor="model">Model</label>
          <input id="model" placeholder="gpt-4.1-mini" value={model} onChange={(event) => onModelChange(event.target.value)} />

          <label htmlFor="api-key">API key</label>
          <input
            id="api-key"
            placeholder="Stored locally"
            type="password"
            value={apiKey}
            onChange={(event) => onApiKeyChange(event.target.value)}
          />

          <label htmlFor="outbound-policy">Outbound policy</label>
          <select
            id="outbound-policy"
            value={outboundContextPolicy}
            onChange={(event) => onOutboundContextPolicyChange(event.target.value)}
          >
            <option value="snippets_only">Snippets only</option>
            <option value="full_text">Full text</option>
            <option value="local_only">Local only</option>
          </select>

          <button type="submit">Save settings</button>
        </form>
      </section>
    </div>
  );
}
