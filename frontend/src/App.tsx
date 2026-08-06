import { useEffect, useState } from 'react';
import { api } from './api/client';
import type { Repository, ReviewItem, ReviewDetails } from './types';
import { 
  GitPullRequest, FolderGit2, RefreshCw, X, Code2, 
  Search, Play, Settings, ShieldCheck, Cpu 
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'reviews' | 'repos'>('reviews');
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedReview, setSelectedReview] = useState<ReviewDetails | null>(null);

  // Состояния для поиска и фильтрации
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Состояния для модалок
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testForm, setTestForm] = useState({ title: '', author: 'yaroslav_dev', pr_number: 101 });
  const [editingRepo, setEditingRepo] = useState<Repository | null>(null);
  const [rulesJsonText, setRulesJsonText] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [reviewsData, reposData] = await Promise.all([
        api.getReviews(),
        api.getRepositories(),
      ]);
      setReviews(reviewsData);
      setRepos(reposData);
    } catch (err) {
      console.error("Ошибка загрузки данных:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openReviewModal = async (reviewId: string) => {
    try {
      const details = await api.getReviewDetails(reviewId);
      setSelectedReview(details);
    } catch (err) {
      alert("Не удалось загрузить детали ревью");
    }
  };

  const handleRunTest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.triggerTestReview(testForm);
      setIsTestModalOpen(false);
      setTestForm({ title: '', author: 'yaroslav_dev', pr_number: Math.floor(Math.random() * 900) + 100 });
      await loadData();
    } catch (err) {
      alert("Ошибка при запуске тестового ревью");
    }
  };

  const handleSaveRules = async () => {
    if (!editingRepo) return;
    try {
      const parsedRules = JSON.parse(rulesJsonText);
      await api.updateRepository(editingRepo.id, { custom_rules: parsedRules });
      setEditingRepo(null);
      await loadData();
    } catch (err) {
      alert("Неверный формат JSON правил!");
    }
  };

  const toggleRepoStatus = async (repo: Repository) => {
    try {
      await api.updateRepository(repo.id, { is_active: !repo.is_active });
      await loadData();
    } catch (err) {
      alert("Не удалось изменить статус репозитория");
    }
  };

  // Вычисляемые показатели (Метрики)
  const completedReviews = reviews.filter(r => r.score !== null);
  const avgScore = completedReviews.length > 0 
    ? Math.round(completedReviews.reduce((acc, r) => acc + (r.score || 0), 0) / completedReviews.length) 
    : 0;

  // Отфильтрованные ревью
  const filteredReviews = reviews.filter(r => {
    const matchesSearch = r.pr_title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          r.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          r.repo_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getScoreBadge = (score: number | null) => {
    if (score === null) return <span className="bg-slate-800 text-slate-400 px-2.5 py-1 rounded-full text-xs font-medium">Pending</span>;
    if (score >= 80) return <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full text-xs font-bold">🟢 {score}/100</span>;
    if (score >= 50) return <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-1 rounded-full text-xs font-bold">🟡 {score}/100</span>;
    return <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2.5 py-1 rounded-full text-xs font-bold">🔴 {score}/100</span>;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500 selection:text-white">
      {/* HEADER */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-tr from-indigo-600 to-purple-600 p-2.5 rounded-xl text-white shadow-lg shadow-indigo-500/20">
              <Code2 className="w-6 h-6" />
            </div>
            <span className="font-extrabold text-xl tracking-wider bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
              Revio AI Dashboard
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button 
              onClick={() => setIsTestModalOpen(true)}
              className="flex items-center space-x-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium px-4 py-2 rounded-xl text-sm shadow-lg shadow-indigo-500/25 transition cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Запустить тест AI</span>
            </button>

            <button 
              onClick={loadData}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 transition cursor-pointer"
              title="Обновить данные"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        
        {/* STATS OVERVIEW CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex items-center space-x-4">
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Средняя оценка качества</p>
              <h4 className="text-2xl font-bold text-slate-100">{avgScore} <span className="text-sm font-normal text-slate-500">/ 100</span></h4>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex items-center space-x-4">
            <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/20">
              <GitPullRequest className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Проведено ревью</p>
              <h4 className="text-2xl font-bold text-slate-100">{reviews.length}</h4>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex items-center space-x-4">
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Активные репозитории</p>
              <h4 className="text-2xl font-bold text-slate-100">{repos.filter(r => r.is_active).length} <span className="text-sm font-normal text-slate-500">/ {repos.length}</span></h4>
            </div>
          </div>
        </div>

        {/* TABS & SEARCH BAR */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex space-x-4">
            <button
              onClick={() => setActiveTab('reviews')}
              className={`pb-2 px-1 flex items-center space-x-2 font-semibold text-sm transition cursor-pointer border-b-2 ${
                activeTab === 'reviews'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitPullRequest className="w-4 h-4" />
              <span>Лента AI-Ревью ({filteredReviews.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('repos')}
              className={`pb-2 px-1 flex items-center space-x-2 font-semibold text-sm transition cursor-pointer border-b-2 ${
                activeTab === 'repos'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <FolderGit2 className="w-4 h-4" />
              <span>Репозитории ({repos.length})</span>
            </button>
          </div>

          {/* SEARCH & FILTERS (Only for reviews tab) */}
          {activeTab === 'reviews' && (
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Поиск PR или автора..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition w-48 sm:w-64"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-xs text-slate-300 rounded-xl px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">Все статусы</option>
                <option value="completed">Completed</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          )}
        </div>

        {/* TAB 1: REVIEWS LIST */}
        {activeTab === 'reviews' && (
          <div className="space-y-3">
            {filteredReviews.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/30 border border-dashed border-slate-800 rounded-2xl">
                <Cpu className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-400 font-medium">Записей ревью не найдено</p>
                <p className="text-xs text-slate-600 mt-1">Попробуй запустить тест через кнопку в шапке</p>
              </div>
            ) : (
              filteredReviews.map((r) => (
                <div
                  key={r.id}
                  onClick={() => openReviewModal(r.id)}
                  className="bg-slate-900/70 border border-slate-800/80 hover:border-indigo-500/50 p-5 rounded-2xl transition cursor-pointer flex items-center justify-between group shadow-sm hover:shadow-indigo-500/5"
                >
                  <div className="space-y-2 max-w-2xl">
                    <div className="flex items-center space-x-2.5">
                      <span className="text-xs font-mono bg-indigo-950/80 text-indigo-300 px-2.5 py-0.5 rounded-md border border-indigo-800/40">
                        {r.repo_name}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">PR #{r.pr_number}</span>
                      <span className="text-xs text-slate-500 font-mono">author: @{r.author}</span>
                    </div>
                    <h3 className="font-semibold text-base text-slate-100 group-hover:text-indigo-300 transition">
                      {r.pr_title}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-1 leading-relaxed">{r.summary || 'Обработка кода в процессе...'}</p>
                  </div>

                  <div className="flex flex-col items-end space-y-2">
                    {getScoreBadge(r.score)}
                    <span className="text-[11px] text-slate-500 font-mono">
                      {new Date(r.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 2: REPOSITORIES */}
        {activeTab === 'repos' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {repos.map((repo) => (
              <div key={repo.id} className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl space-y-5 flex flex-col justify-between">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <FolderGit2 className="w-5 h-5 text-indigo-400" />
                      <h3 className="font-bold text-slate-100">{repo.full_name}</h3>
                    </div>

                    <button
                      onClick={() => toggleRepoStatus(repo)}
                      className={`text-xs px-3 py-1 rounded-full font-medium border transition cursor-pointer ${
                        repo.is_active
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20'
                      }`}
                    >
                      {repo.is_active ? 'Active' : 'Disabled'}
                    </button>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-400 space-y-1">
                    <span className="text-indigo-400 font-semibold block mb-2">Кастомные правила (custom_rules):</span>
                    <pre className="overflow-x-auto">{JSON.stringify(repo.custom_rules, null, 2)}</pre>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => {
                      setEditingRepo(repo);
                      setRulesJsonText(JSON.stringify(repo.custom_rules, null, 2));
                    }}
                    className="w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-medium border border-slate-700 transition cursor-pointer"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>Настроить правила AI</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* MODAL 1: TEST REVIEW TRIGGER */}
      {isTestModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="font-bold text-lg text-slate-100">Запустить AI-Ревью</h3>
              <button onClick={() => setIsTestModalOpen(false)} className="text-slate-400 hover:text-slate-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRunTest} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400">Заголовок Pull Request</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Add Redis cache layer for user service"
                  value={testForm.title}
                  onChange={(e) => setTestForm({ ...testForm, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400">Автор PR</label>
                  <input
                    type="text"
                    required
                    value={testForm.author}
                    onChange={(e) => setTestForm({ ...testForm, author: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400">Номер PR</label>
                  <input
                    type="number"
                    required
                    value={testForm.pr_number}
                    onChange={(e) => setTestForm({ ...testForm, pr_number: parseInt(e.target.value) || 1 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl text-sm transition cursor-pointer mt-2"
              >
                Отправить в очередь AI Engine
              </button>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDIT CUSTOM RULES */}
      {editingRepo && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-lg text-slate-100">Правила для {editingRepo.full_name}</h3>
              <button onClick={() => setEditingRepo(null)} className="text-slate-400 hover:text-slate-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-400">Редактирование конфигурации (JSON)</label>
              <textarea
                rows={8}
                value={rulesJsonText}
                onChange={(e) => setRulesJsonText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-indigo-300 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              onClick={handleSaveRules}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 rounded-xl text-sm transition cursor-pointer"
            >
              Сохранить изменения
            </button>
          </div>
        </div>
      )}

      {/* MODAL 3: REVIEW DETAILS */}
      {selectedReview && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 w-full max-w-3xl rounded-2xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Детализация AI-Ревью</h2>
                <span className="text-xs text-slate-400 font-mono">ID: {selectedReview.review.id}</span>
              </div>
              <button
                onClick={() => setSelectedReview(null)}
                className="text-slate-400 hover:text-slate-100 p-1 rounded-lg hover:bg-slate-800 transition cursor-pointer"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Резюме AI</span>
                <p className="text-sm text-slate-200 leading-relaxed">{selectedReview.review.summary}</p>
              </div>

              <div className="space-y-3">
                <h4 className="font-semibold text-sm text-slate-300">
                  Замечания к коду ({selectedReview.comments.length})
                </h4>

                {selectedReview.comments.map((c) => (
                  <div key={c.id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-indigo-300 bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-800/40">
                        {c.file_path}:{c.line_number}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-bold ${
                          c.severity === 'critical'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : c.severity === 'warning'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        }`}
                      >
                        {c.severity.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-sm text-slate-300">{c.comment_text}</p>

                    {c.suggested_code && (
                      <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-xs text-emerald-400 overflow-x-auto">
                        <pre>{c.suggested_code}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}