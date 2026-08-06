import axios from 'axios';
import type { Repository, ReviewItem, ReviewDetails } from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
  getRepositories: async (): Promise<Repository[]> => {
    const res = await axios.get(`${API_BASE}/repositories`);
    return res.data;
  },

  getReviews: async (): Promise<ReviewItem[]> => {
    const res = await axios.get(`${API_BASE}/reviews`);
    return res.data;
  },

  getReviewDetails: async (reviewId: string): Promise<ReviewDetails> => {
    const res = await axios.get(`${API_BASE}/reviews/${reviewId}`);
    return res.data;
  },

  updateRepository: async (repoId: string, data: { is_active?: boolean; custom_rules?: any }): Promise<Repository> => {
    const res = await axios.patch(`${API_BASE}/repositories/${repoId}`, data);
    return res.data;
  },

  triggerTestReview: async (data: { title: string; author: string; pr_number: number }) => {
    const res = await axios.post(`${API_BASE}/test-review`, data);
    return res.data;
  },
};