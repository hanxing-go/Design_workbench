import markup from './designPanel.html?raw';
import './designPanel.css';
import type { Point, Summary } from './types';

type Budget = {
  tool_calls: number;
  model_calls: number;
  seconds: number;
  tokens: number;
  revisions: number;
  cost_usd: number | null;
};
type Candidate = {
  candidate_id: string;
  name: string;
  revision: number;
  feedback: string;
  screenshots?: { images: { url: string }[] }[];
};
type Run = {
  run_id: string;
  project: string;
  prompt: string;
  model: string;
  status: string;
  stage: string;
  message: string;
  budget: Budget;
  elapsed_seconds: number;
  usage: {
    tool_calls: number;
    model_calls: number;
    revisions: number;
    input_tokens: number;
    output_tokens: number;
    cached_input_tokens: number;
    cost_usd: number | null;
    source: string;
  };
  pending: {
    proposal_id: string;
    expected_revision: number;
    explanation: string;
    preview: {
      changed: number;
      truncated: boolean;
      changes: { position: Point; after: unknown }[];
    };
  } | null;
  candidates: Candidate[];
  events: { at: number; message: string }[];
};
type Hooks = {
  project: () => string;
  summary: () => Summary | null;
  refresh: () => Promise<void>;
  preview: (changes: { position: Point; after: unknown }[] | null) => void;
  openProject: (id: string) => Promise<void>;
  notice: (text: string, error?: boolean) => void;
};
const labels: Record<string, string> = {
  active: '进行中',
  awaiting_approval: '等待确认改稿',
  cancelled: '已取消',
  failed: '发生错误',
  budget_exceeded: '预算已用完',
  interrupted: '运行已中断',
  succeeded: '已完成',
  planning: '理解需求与规划',
  building: '生成初稿',
  reviewing: '查看实际画面',
  revising: '局部改稿',
  exporting: '保存与导出',
};

export class DesignPanel {
  private run: Run | null = null;
  private loading = false;
  private polling = false;
  private generation = 0;
  private displayedProposal = '';
  private readonly node: HTMLElement;

  constructor(private hooks: Hooks) {
    document.querySelector('#app')!.insertAdjacentHTML('beforeend', markup);
    this.node = this.el('ai-panel');
    this.el('ai-tasks').onclick = () => {
      this.node.hidden = !this.node.hidden;
      if (!this.node.hidden)
        void this.safe(async () => {
          await this.load();
        });
    };
    this.el('ai-close').onclick = () => {
      this.node.hidden = true;
    };
    this.el('ai-new').onclick = () => {
      this.el('ai-create-form').hidden = false;
    };
    this.el<HTMLSelectElement>('ai-runs').onchange = () =>
      void this.safe(async () => {
        const id = this.value('ai-runs');
        this.run = id ? await this.api<Run>(`/api/design-runs/${id}`) : null;
        this.render();
      });
    this.el<HTMLFormElement>('ai-create-form').onsubmit = (event) => {
      event.preventDefault();
      void this.safe(async () => {
        const summary = this.hooks.summary();
        if (!summary) throw new Error('请先选择项目');
        const run = await this.api<Run>(`/api/projects/${this.hooks.project()}/design-runs`, {
          project: this.hooks.project(),
          expected_revision: summary.revision,
          request_id: crypto.randomUUID(),
          prompt: this.value('ai-prompt').trim(),
          model: this.value('ai-model').trim(),
          auto_build: this.el<HTMLInputElement>('ai-auto-build').checked,
          budget: this.budget(''),
        });
        await this.load(run.run_id);
        this.hooks.notice('任务已创建，将编号交给 AI 后即可开始');
      });
    };
    this.el('ai-cancel').onclick = () => void this.act('cancel');
    this.el('ai-resume').onclick = () => void this.act('resume');
    this.el('ai-finish').onclick = () =>
      void this.act('finish', { outcome: 'succeeded', message: '用户确认候选稿可用，任务完成' });
    this.el('ai-extend').onclick = () => {
      if (!this.run) return;
      const fields = this.el('ai-budget').cloneNode(true) as HTMLElement;
      fields.id = 'ai-extended-budget';
      fields.querySelectorAll<HTMLInputElement>('input').forEach((input) => {
        input.id += '-extend';
      });
      this.el('ai-extend-fields').replaceChildren(fields);
      const budget = this.run.budget;
      for (const [id, value] of Object.entries({
        calls: budget.tool_calls,
        'model-calls': budget.model_calls,
        minutes: Math.ceil(budget.seconds / 60),
        tokens: budget.tokens,
        revisions: budget.revisions,
        cost: budget.cost_usd ?? '',
      })) {
        this.el<HTMLInputElement>(`ai-budget-${id}-extend`).value = String(value);
      }
      this.el('ai-extend-form').hidden = false;
    };
    this.el<HTMLFormElement>('ai-extend-form').onsubmit = (event) => {
      event.preventDefault();
      void this.act('resume', { budget: this.budget('-extend') });
    };
    this.el('ai-view-proposal').onclick = () => {
      if (this.run?.pending) {
        this.displayedProposal = this.run.pending.proposal_id;
        this.hooks.preview(this.run.pending.preview.changes);
        this.node.hidden = true;
        this.hooks.notice('AI 改稿已显示在画布；打开 AI 任务面板确认或拒绝');
      }
    };
    this.el('ai-approve').onclick = () => void this.decide(true);
    this.el('ai-reject').onclick = () => void this.decide(false);
    this.el<HTMLFormElement>('ai-candidate-form').onsubmit = (event) => {
      event.preventDefault();
      void this.safe(async () => {
        if (!this.run || !this.hooks.summary()) return;
        await this.api(`/api/design-runs/${this.run.run_id}/candidates`, {
          ...this.action(),
          name: this.value('ai-candidate-name').trim(),
          feedback: this.value('ai-candidate-feedback').trim(),
          expected_revision: this.hooks.summary()!.revision,
        });
        this.el<HTMLInputElement>('ai-candidate-name').value = '';
        await this.poll();
        this.hooks.notice('候选稿已保存，后续修改不会改变这份工程');
      });
    };
    const timer = window.setInterval(() => {
      if (!document.hidden && !this.loading)
        void this.poll().catch((error: unknown) => {
          this.el('ai-error').textContent = error instanceof Error ? error.message : '读取任务失败';
        });
    }, 1500);
    window.addEventListener('pagehide', () => window.clearInterval(timer), { once: true });
  }

  private el<T extends HTMLElement = HTMLElement>(id: string): T {
    return document.getElementById(id) as T;
  }
  private value(id: string) {
    return this.el<HTMLInputElement>(id).value;
  }
  private async api<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok || result.error)
      throw new Error(result.error?.message ?? `请求失败 ${response.status}`);
    return result as T;
  }
  private action() {
    return { run_id: this.run!.run_id, request_id: crypto.randomUUID() };
  }
  private budget(suffix: string): Budget {
    const number = (id: string) => Number(this.value(`ai-budget-${id}${suffix}`));
    return {
      tool_calls: number('calls'),
      model_calls: number('model-calls'),
      seconds: number('minutes') * 60,
      tokens: number('tokens'),
      revisions: number('revisions'),
      cost_usd: this.value(`ai-budget-cost${suffix}`) ? number('cost') : null,
    };
  }
  private async safe(action: () => Promise<void>) {
    if (this.loading) return;
    this.loading = true;
    this.el('ai-error').textContent = '';
    this.node
      .querySelectorAll<HTMLButtonElement>('button')
      .forEach((button) => (button.disabled = true));
    try {
      await action();
    } catch (error) {
      const text = error instanceof Error ? error.message : '操作失败';
      this.el('ai-error').textContent = text;
      this.hooks.notice(text, true);
      await this.poll().catch(() => {});
    } finally {
      this.loading = false;
      this.node
        .querySelectorAll<HTMLButtonElement>('button')
        .forEach((button) => (button.disabled = false));
      this.render();
    }
  }
  private async act(action: string, extra: Record<string, unknown> = {}) {
    await this.safe(async () => {
      if (!this.run) return;
      this.run = await this.api<Run>(`/api/design-runs/${this.run.run_id}/${action}`, {
        ...this.action(),
        ...extra,
      });
      this.el('ai-extend-form').hidden = true;
      this.render();
    });
  }
  private async decide(approve: boolean) {
    await this.safe(async () => {
      if (!this.run?.pending) return;
      this.run = await this.api<Run>(`/api/design-runs/${this.run.run_id}/decision`, {
        ...this.action(),
        proposal_id: this.run.pending.proposal_id,
        approve,
      });
      this.hooks.preview(null);
      this.displayedProposal = '';
      await this.hooks.refresh();
      this.render();
    });
  }

  async load(preferred?: string) {
    const project = this.hooks.project();
    const generation = ++this.generation;
    this.run = null;
    if (this.displayedProposal) this.hooks.preview(null);
    this.displayedProposal = '';
    if (!project) return;
    const result = await this.api<{ items: Run[] }>(`/api/projects/${project}/design-runs`);
    if (generation !== this.generation || project !== this.hooks.project()) return;
    const select = this.el<HTMLSelectElement>('ai-runs');
    select.replaceChildren(
      ...result.items.map(
        (run) =>
          new Option(
            `${labels[run.status] ?? run.status} · ${run.prompt.slice(0, 25)}`,
            run.run_id,
          ),
      ),
    );
    this.run = result.items.find((run) => run.run_id === preferred) ?? result.items[0] ?? null;
    if (this.run) select.value = this.run.run_id;
    this.el('ai-create-form').hidden = !!this.run;
    this.el('ai-extend-form').hidden = true;
    const auto = this.el<HTMLInputElement>('ai-auto-build');
    auto.disabled = !!this.hooks.summary()?.blocks;
    if (auto.disabled) auto.checked = false;
    this.render();
  }
  private async poll() {
    if (this.polling || !this.run) return;
    this.polling = true;
    const run = this.run;
    const generation = this.generation;
    try {
      const result = await this.api<Run>(`/api/design-runs/${run.run_id}`);
      if (generation !== this.generation || this.run?.run_id !== run.run_id) return;
      this.run = result;
      this.render();
    } finally {
      this.polling = false;
    }
  }
  private render() {
    const run = this.run;
    this.el('ai-detail').hidden = !run;
    this.el('ai-tasks').textContent = run?.pending ? 'AI 任务 · 待确认' : 'AI 任务';
    if (!run) return;
    this.el('ai-run-title').textContent = run.prompt;
    this.el<HTMLInputElement>('ai-run-id').value = run.run_id;
    this.el('ai-state').textContent =
      `${labels[run.status] ?? run.status} · ${labels[run.stage] ?? run.stage}`;
    this.el('ai-progress').textContent = run.message;
    const selected = this.el<HTMLSelectElement>('ai-runs').selectedOptions[0];
    if (selected)
      selected.textContent = `${labels[run.status] ?? run.status} · ${run.prompt.slice(0, 25)}`;
    const used = run.usage;
    const format = (value: number) => value.toLocaleString();
    const tokens = used.source
      ? `${format(used.input_tokens + used.output_tokens)} / ${format(run.budget.tokens)}`
      : `尚未报告 / ${format(run.budget.tokens)}`;
    this.el('ai-usage').replaceChildren(
      ...[
        `工具 ${used.tool_calls} / ${run.budget.tool_calls} 次`,
        `模型调用 ${used.source ? used.model_calls : '尚未报告'} / ${run.budget.model_calls} 次`,
        `时长 ${(run.elapsed_seconds / 60).toFixed(1)} / ${(run.budget.seconds / 60).toFixed(1)} 分钟`,
        `修改 ${used.revisions} / ${run.budget.revisions} 批`,
        `Tokens ${tokens}`,
        `费用 ${used.cost_usd === null ? '尚未报告' : '$' + used.cost_usd.toFixed(4)}${run.budget.cost_usd === null ? '' : ' / $' + run.budget.cost_usd}`,
      ].map((text) => {
        const row = document.createElement('span');
        row.textContent = text;
        return row;
      }),
    );
    this.el('ai-usage-source').textContent = used.source
      ? `模型：${run.model || '未记录'}；用量来源：${used.source}。缓存输入包含在输入总量中。`
      : '外部 AI 尚未回报模型用量；工具与时长预算由工作台计量。';
    const stopped = ['cancelled', 'failed', 'budget_exceeded', 'interrupted'].includes(run.status);
    this.el('ai-cancel').hidden = !['active', 'awaiting_approval'].includes(run.status);
    this.el('ai-resume').hidden = !stopped || run.status === 'budget_exceeded';
    this.el('ai-extend').hidden = !stopped;
    this.el('ai-finish').hidden = run.status !== 'active' || !run.candidates.length;
    this.el('ai-proposal').hidden = !run.pending || run.status !== 'awaiting_approval';
    if (run.pending) {
      this.el('ai-proposal-message').textContent = run.pending.explanation;
      this.el('ai-proposal-count').textContent =
        `基于 r${run.pending.expected_revision}，将修改 ${format(run.pending.preview.changed)} 格。${run.pending.preview.truncated ? '画布预演显示前 10,000 格。' : ''}`;
    } else if (this.displayedProposal) {
      this.hooks.preview(null);
      this.displayedProposal = '';
    }
    this.el('ai-candidates').replaceChildren(
      ...run.candidates.map((candidate) => {
        const card = document.createElement('article');
        card.className = 'ai-candidate';
        const title = document.createElement('strong');
        title.textContent = `${candidate.name} · r${candidate.revision}`;
        const detail = document.createElement('p');
        detail.textContent = candidate.feedback;
        const pictures = document.createElement('div');
        pictures.className = 'ai-candidate-images';
        for (const shot of candidate.screenshots ?? []) {
          for (const item of shot.images) {
            const link = document.createElement('a');
            link.href = item.url;
            link.target = '_blank';
            link.rel = 'noopener';
            const image = document.createElement('img');
            image.src = item.url;
            image.alt = `${candidate.name}，修订 ${candidate.revision} 的实际截图`;
            image.loading = 'lazy';
            link.append(image);
            pictures.append(link);
          }
        }
        const open = document.createElement('button');
        open.textContent = '打开副本继续修改';
        open.onclick = () =>
          void this.safe(async () => {
            const result = await this.api<{ project_id: string }>(
              `/api/design-runs/${run.run_id}/candidates/${candidate.candidate_id}/open`,
              { request_id: crypto.randomUUID() },
            );
            await this.hooks.openProject(result.project_id);
          });
        const download = document.createElement('a');
        download.href = `/api/design-runs/${run.run_id}/candidates/${candidate.candidate_id}/download`;
        download.textContent = '下载工程';
        card.append(title, detail, pictures, open, download);
        return card;
      }),
    );
    this.el('ai-events').replaceChildren(
      ...run.events
        .slice(-20)
        .reverse()
        .map((event) => {
          const item = document.createElement('li');
          item.textContent = `${new Date(event.at * 1000).toLocaleTimeString()} · ${event.message}`;
          return item;
        }),
    );
  }
}
