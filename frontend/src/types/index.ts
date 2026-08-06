export interface Repository {
  id: string;
  github_repo_id: number;
  full_name: string;
  is_active: boolean;
  custom_rules: Record<string, any>;
  created_at: string;
}

export interface ReviewItem {
  id: string;
  repo_name: string;
  pr_number: number;
  pr_title: string;
  author: string;
  commit_sha: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  score: number | null;
  summary: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface ReviewComment {
  id: string;
  file_path: string;
  line_number: number;
  severity: 'info' | 'warning' | 'critical';
  comment_text: string;
  suggested_code: string | null;
}

export interface ReviewDetails {
  review: {
    id: string;
    commit_sha: string;
    status: string;
    score: number;
    summary: string;
    tokens_used: number;
    started_at: string;
  };
  comments: ReviewComment[];
}