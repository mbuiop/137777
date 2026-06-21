// 4_admin_dashboard.jsx
/**
 * Instagram Clone - Admin Dashboard
 * Complete admin panel with analytics, user management, content moderation
 */

import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  createContext,
  useContext,
  lazy,
  Suspense
} from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useParams,
  useLocation
} from 'react-router-dom';
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
  useQueryClient
} from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster, toast } from 'react-hot-toast';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar, Doughnut, PolarArea } from 'react-chartjs-2';
import { format, formatDistanceToNow, subDays, subMonths } from 'date-fns';
import { useInView } from 'react-intersection-observer';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

// =============================================
// Chart.js Registration
// =============================================
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// =============================================
// Admin API Client
// =============================================
class AdminApiClient {
  constructor() {
    this.baseURL = '/api/admin';
    this.token = localStorage.getItem('admin_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('admin_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('admin_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/admin/login';
      throw new Error('Unauthorized');
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Request failed');
    }
    return data;
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }

  // Admin specific endpoints
  async getDashboardStats() {
    return this.get('/stats');
  }

  async getUsers(params = {}) {
    return this.get('/users', { params });
  }

  async getUserDetails(userId) {
    return this.get(`/users/${userId}`);
  }

  async updateUser(userId, data) {
    return this.put(`/users/${userId}`, data);
  }

  async deleteUser(userId) {
    return this.delete(`/users/${userId}`);
  }

  async getPosts(params = {}) {
    return this.get('/posts', { params });
  }

  async getPostDetails(postId) {
    return this.get(`/posts/${postId}`);
  }

  async deletePost(postId) {
    return this.delete(`/posts/${postId}`);
  }

  async moderatePost(postId, action) {
    return this.post(`/posts/${postId}/moderate`, { action });
  }

  async getAnalytics(params = {}) {
    return this.get('/analytics', { params });
  }

  async getReports(params = {}) {
    return this.get('/reports', { params });
  }

  async resolveReport(reportId, action) {
    return this.post(`/reports/${reportId}/resolve`, { action });
  }

  async getSystemLogs(params = {}) {
    return this.get('/logs', { params });
  }

  async getModerationQueue(params = {}) {
    return this.get('/moderation/queue', { params });
  }

  async performModeration(postId, action) {
    return this.post(`/moderation/${postId}`, { action });
  }

  async getSettings() {
    return this.get('/settings');
  }

  async updateSettings(settings) {
    return this.put('/settings', settings);
  }

  async generateReport(type, params = {}) {
    return this.post(`/reports/generate/${type}`, params);
  }

  async exportData(type, params = {}) {
    return this.post(`/export/${type}`, params);
  }
}

const adminApi = new AdminApiClient();

// =============================================
// Query Client
// =============================================
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30000,
      cacheTime: 60000,
      retry: 1,
    },
  },
});

// =============================================
// Admin Context
// =============================================
const AdminContext = createContext(null);

const AdminProvider = ({ children }) => {
  const [adminUser, setAdminUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAdmin = async () => {
      try {
        const token = localStorage.getItem('admin_token');
        if (token) {
          const response = await adminApi.get('/me');
          setAdminUser(response);
        }
      } catch (error) {
        console.error('Admin initialization error:', error);
        adminApi.clearToken();
      } finally {
        setLoading(false);
      }
    };
    initAdmin();
  }, []);

  const login = async (username, password) => {
    const response = await adminApi.post('/login', { username, password });
    adminApi.setToken(response.token);
    setAdminUser(response.user);
    return response;
  };

  const logout = () => {
    adminApi.clearToken();
    setAdminUser(null);
  };

  return (
    <AdminContext.Provider value={{ adminUser, loading, login, logout }}>
      {children}
    </AdminContext.Provider>
  );
};

const useAdmin = () => {
  const context = useContext(AdminContext);
  if (!context) throw new Error('useAdmin must be used within AdminProvider');
  return context;
};

// =============================================
// Admin Layout Components
// =============================================
const Sidebar = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'users', icon: '👥', label: 'Users' },
    { id: 'posts', icon: '📸', label: 'Posts' },
    { id: 'moderation', icon: '🔍', label: 'Moderation' },
    { id: 'reports', icon: '⚠️', label: 'Reports' },
    { id: 'analytics', icon: '📈', label: 'Analytics' },
    { id: 'settings', icon: '⚙️', label: 'Settings' },
    { id: 'logs', icon: '📋', label: 'Logs' },
  ];

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen sticky top-0 overflow-y-auto">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <span className="text-2xl">📸</span>
          <span className="text-xl font-bold bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
            Admin
          </span>
        </div>

        <nav className="space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${
                activeTab === item.id
                  ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/25'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
              {item.id === 'moderation' && (
                <span className="ml-auto bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  12
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {}}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition"
          >
            <span className="text-xl">🔔</span>
            <span className="font-medium">Notifications</span>
          </button>
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition">
            <span className="text-xl">💬</span>
            <span className="font-medium">Support Chat</span>
          </button>
        </div>
      </div>
    </div>
  );
};

const AdminHeader = ({ onLogout }) => {
  const { adminUser } = useAdmin();

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Welcome back, {adminUser?.full_name || 'Admin'}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition relative">
            <span className="text-xl">🔔</span>
            <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          </button>

          <button
            onClick={onLogout}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

// =============================================
// Dashboard Component
// =============================================
const Dashboard = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin_stats'],
    queryFn: adminApi.getDashboardStats,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return <div className="flex justify-center items-center h-96"><div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;
  }

  const statCards = [
    { label: 'Total Users', value: stats?.total_users?.toLocaleString() || '0', icon: '👥', color: 'blue' },
    { label: 'Total Posts', value: stats?.total_posts?.toLocaleString() || '0', icon: '📸', color: 'purple' },
    { label: 'Active Users', value: stats?.active_users?.toLocaleString() || '0', icon: '🟢', color: 'green' },
    { label: 'Reports', value: stats?.total_reports?.toLocaleString() || '0', icon: '⚠️', color: 'red' },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover:shadow-md transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
                <p className="text-3xl font-bold mt-2">{stat.value}</p>
              </div>
              <div className={`text-4xl w-16 h-16 rounded-full bg-${stat.color}-100 dark:bg-${stat.color}-900/20 flex items-center justify-center`}>
                {stat.icon}
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className={`text-sm ${stats?.changes?.[stat.label]?.positive ? 'text-green-500' : 'text-red-500'}`}>
                {stats?.changes?.[stat.label]?.percentage || 0}%
              </span>
              <span className="text-sm text-gray-500">from last month</span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">User Growth</h3>
          <Line
            data={{
              labels: stats?.user_growth?.labels || [],
              datasets: [{
                label: 'New Users',
                data: stats?.user_growth?.data || [],
                borderColor: '#3B82F6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4,
              }]
            }}
            options={{
              responsive: true,
              plugins: {
                legend: { display: false }
              },
              scales: {
                y: { beginAtZero: true }
              }
            }}
          />
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Post Activity</h3>
          <Bar
            data={{
              labels: stats?.post_activity?.labels || [],
              datasets: [{
                label: 'Posts',
                data: stats?.post_activity?.data || [],
                backgroundColor: '#8B5CF6',
                borderRadius: 8,
              }]
            }}
            options={{
              responsive: true,
              plugins: {
                legend: { display: false }
              },
              scales: {
                y: { beginAtZero: true }
              }
            }}
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {stats?.recent_activity?.map((activity, index) => (
            <div key={index} className="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition">
              <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                {activity.icon || '📝'}
              </div>
              <div className="flex-1">
                <p className="text-sm">{activity.description}</p>
                <p className="text-xs text-gray-500">
                  {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Users Management
// =============================================
const UsersManagement = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin_users', page, searchQuery],
    queryFn: () => adminApi.getUsers({ page, search: searchQuery }),
  });

  const deleteUserMutation = useMutation({
    mutationFn: adminApi.deleteUser,
    onSuccess: () => {
      toast.success('User deleted successfully');
      refetch();
    },
    onError: () => toast.error('Failed to delete user'),
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ userId, data }) => adminApi.updateUser(userId, data),
    onSuccess: () => {
      toast.success('User updated successfully');
      refetch();
      setShowUserModal(false);
    },
    onError: () => toast.error('Failed to update user'),
  });

  const handleDeleteUser = (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      deleteUserMutation.mutate(userId);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
          Export Users
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">User</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Email</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Posts</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Followers</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Joined</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Status</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {data?.users?.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <img
                        src={user.profile_pic || 'https://via.placeholder.com/40'}
                        alt={user.username}
                        className="w-10 h-10 rounded-full object-cover"
                      />
                      <div>
                        <p className="font-semibold">{user.username}</p>
                        <p className="text-sm text-gray-500">{user.full_name}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">{user.email}</td>
                  <td className="px-4 py-3">{user.post_count || 0}</td>
                  <td className="px-4 py-3">{user.follower_count || 0}</td>
                  <td className="px-4 py-3">{format(new Date(user.created_at), 'MMM d, yyyy')}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => { setSelectedUser(user); setShowUserModal(true); }}
                        className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Showing {data?.users?.length || 0} of {data?.total || 0} users
        </p>
        <div className="flex gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <button
            disabled={!data?.has_more}
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      {/* User Modal */}
      {showUserModal && selectedUser && (
        <UserModal
          user={selectedUser}
          onClose={() => setShowUserModal(false)}
          onUpdate={(data) => updateUserMutation.mutate({ userId: selectedUser.id, data })}
        />
      )}
    </div>
  );
};

// =============================================
// User Modal Component
// =============================================
const UserModal = ({ user, onClose, onUpdate }) => {
  const [formData, setFormData] = useState({
    full_name: user.full_name || '',
    bio: user.bio || '',
    is_active: user.is_active ?? true,
    is_private: user.is_private ?? false,
    is_verified: user.is_verified ?? false,
  });

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Edit User: {user.username}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition">
            ✕
          </button>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); onUpdate(formData); }} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-1">Bio</label>
            <textarea
              value={formData.bio}
              onChange={(e) => setFormData({...formData, bio: e.target.value})}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium">Active Account</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_private}
                onChange={(e) => setFormData({...formData, is_private: e.target.checked})}
                className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium">Private Account</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_verified}
                onChange={(e) => setFormData({...formData, is_verified: e.target.checked})}
                className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium">Verified Account</span>
            </label>
          </div>

          <button
            type="submit"
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition"
          >
            Update User
          </button>
        </form>
      </motion.div>
    </div>
  );
};

// =============================================
// Posts Management
// =============================================
const PostsManagement = () => {
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState('all');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin_posts', page, filter],
    queryFn: () => adminApi.getPosts({ page, filter }),
  });

  const deletePostMutation = useMutation({
    mutationFn: adminApi.deletePost,
    onSuccess: () => {
      toast.success('Post deleted successfully');
      refetch();
    },
  });

  const moderatePostMutation = useMutation({
    mutationFn: ({ postId, action }) => adminApi.moderatePost(postId, action),
    onSuccess: () => {
      toast.success('Post moderated successfully');
      refetch();
    },
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Posts</option>
          <option value="reported">Reported</option>
          <option value="spam">Spam</option>
          <option value="flagged">Flagged</option>
        </select>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
          Export Posts
        </button>
      </div>

      {/* Posts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.posts?.map((post) => (
          <div key={post.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden hover:shadow-md transition">
            <div className="aspect-square bg-gray-100 dark:bg-gray-700">
              <img
                src={post.media_urls?.[0] || 'https://via.placeholder.com/300'}
                alt="Post"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <img
                  src={post.user?.profile_pic || 'https://via.placeholder.com/24'}
                  alt={post.user?.username}
                  className="w-6 h-6 rounded-full"
                />
                <span className="font-semibold text-sm">{post.user?.username}</span>
              </div>
              <p className="text-sm line-clamp-2">{post.caption}</p>
              <div className="flex items-center justify-between mt-3">
                <div className="flex gap-3 text-sm">
                  <span>❤️ {post.likes_count || 0}</span>
                  <span>💬 {post.comments_count || 0}</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => moderatePostMutation.mutate({ postId: post.id, action: 'approve' })}
                    className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => deletePostMutation.mutate(post.id)}
                    className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Showing {data?.posts?.length || 0} of {data?.total || 0} posts
        </p>
        <div className="flex gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <button
            disabled={!data?.has_more}
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Moderation Queue
// =============================================
const ModerationQueue = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['moderation_queue'],
    queryFn: adminApi.getModerationQueue,
    refetchInterval: 10000,
  });

  const moderateMutation = useMutation({
    mutationFn: ({ postId, action }) => adminApi.performModeration(postId, action),
    onSuccess: () => {
      toast.success('Moderation action completed');
      refetch();
    },
  });

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Moderation Queue</h3>
        <div className="space-y-4">
          {data?.queue?.map((item) => (
            <div key={item.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-start gap-4">
                <img
                  src={item.media_url || 'https://via.placeholder.com/100'}
                  alt="Content"
                  className="w-24 h-24 object-cover rounded-lg"
                />
                <div className="flex-1">
                  <p className="font-semibold">{item.user?.username}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{item.caption}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full text-xs">
                      {item.reason || 'Pending review'}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => moderateMutation.mutate({ postId: item.id, action: 'approve' })}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition text-sm"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => moderateMutation.mutate({ postId: item.id, action: 'reject' })}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition text-sm"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => moderateMutation.mutate({ postId: item.id, action: 'flag' })}
                    className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition text-sm"
                  >
                    Flag
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Analytics Component
// =============================================
const Analytics = () => {
  const [timeRange, setTimeRange] = useState('30d');
  const [reportType, setReportType] = useState('overview');

  const { data, isLoading } = useQuery({
    queryKey: ['admin_analytics', timeRange],
    queryFn: () => adminApi.getAnalytics({ time_range: timeRange }),
  });

  const generateReportMutation = useMutation({
    mutationFn: ({ type, params }) => adminApi.generateReport(type, params),
    onSuccess: (data) => {
      // Download report
      const blob = new Blob([data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${Date.now()}.pdf`;
      a.click();
      toast.success('Report generated successfully');
    },
  });

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap gap-4">
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
          <option value="1y">Last Year</option>
        </select>

        <select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="overview">Overview</option>
          <option value="users">Users</option>
          <option value="engagement">Engagement</option>
          <option value="content">Content</option>
        </select>

        <button
          onClick={() => generateReportMutation.mutate({ type: reportType, params: { timeRange } })}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          Generate Report
        </button>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Engagement Overview</h3>
          <Line
            data={{
              labels: data?.engagement?.labels || [],
              datasets: [
                {
                  label: 'Likes',
                  data: data?.engagement?.likes || [],
                  borderColor: '#3B82F6',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  fill: true,
                },
                {
                  label: 'Comments',
                  data: data?.engagement?.comments || [],
                  borderColor: '#8B5CF6',
                  backgroundColor: 'rgba(139, 92, 246, 0.1)',
                  fill: true,
                }
              ]
            }}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'top',
                },
              },
              scales: {
                y: { beginAtZero: true }
              }
            }}
          />
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Content Distribution</h3>
          <Doughnut
            data={{
              labels: ['Images', 'Videos', 'Carousels'],
              datasets: [{
                data: data?.content_distribution || [60, 25, 15],
                backgroundColor: ['#3B82F6', '#8B5CF6', '#EC4899'],
                borderWidth: 0,
              }]
            }}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'bottom',
                },
              },
            }}
          />
        </div>
      </div>

      {/* Stats Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Detailed Statistics</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-2 text-left text-sm font-semibold">Metric</th>
                <th className="px-4 py-2 text-left text-sm font-semibold">Current</th>
                <th className="px-4 py-2 text-left text-sm font-semibold">Previous</th>
                <th className="px-4 py-2 text-left text-sm font-semibold">Change</th>
              </tr>
            </thead>
            <tbody>
              {data?.stats?.map((stat, index) => (
                <tr key={index} className="border-b border-gray-100 dark:border-gray-700">
                  <td className="px-4 py-2">{stat.metric}</td>
                  <td className="px-4 py-2 font-semibold">{stat.current}</td>
                  <td className="px-4 py-2 text-gray-500">{stat.previous}</td>
                  <td className={`px-4 py-2 ${stat.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {stat.change >= 0 ? '+' : ''}{stat.change}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Reports Management
// =============================================
const ReportsManagement = () => {
  const [filter, setFilter] = useState('all');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin_reports', filter],
    queryFn: () => adminApi.getReports({ filter }),
  });

  const resolveReportMutation = useMutation({
    mutationFn: ({ reportId, action }) => adminApi.resolveReport(reportId, action),
    onSuccess: () => {
      toast.success('Report resolved');
      refetch();
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Reports</option>
          <option value="pending">Pending</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="space-y-4 p-4">
          {data?.reports?.map((report) => (
            <div key={report.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">
                      {report.type}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      report.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                      report.status === 'resolved' ? 'bg-green-100 text-green-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {report.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm">{report.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Reported by {report.reporter?.username} • {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                  </p>
                </div>
                {report.status === 'pending' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => resolveReportMutation.mutate({ reportId: report.id, action: 'resolve' })}
                      className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition"
                    >
                      Resolve
                    </button>
                    <button
                      onClick={() => resolveReportMutation.mutate({ reportId: report.id, action: 'dismiss' })}
                      className="px-3 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600 transition"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Settings Component
// =============================================
const Settings = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin_settings'],
    queryFn: adminApi.getSettings,
  });

  const updateSettingsMutation = useMutation({
    mutationFn: adminApi.updateSettings,
    onSuccess: () => {
      toast.success('Settings updated successfully');
      refetch();
    },
  });

  const [formData, setFormData] = useState({});

  useEffect(() => {
    if (data) {
      setFormData(data);
    }
  }, [data]);

  const handleSubmit = (e) => {
    e.preventDefault();
    updateSettingsMutation.mutate(formData);
  };

  return (
    <div className="space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Platform Settings</h3>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <h4 className="font-semibold mb-2">General Settings</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Platform Name</label>
                <input
                  type="text"
                  value={formData.platform_name || ''}
                  onChange={(e) => setFormData({...formData, platform_name: e.target.value})}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Upload Size (MB)</label>
                <input
                  type="number"
                  value={formData.max_upload_size || 50}
                  onChange={(e) => setFormData({...formData, max_upload_size: parseInt(e.target.value)})}
                  className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Moderation Settings</h4>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.auto_moderation || false}
                  onChange={(e) => setFormData({...formData, auto_moderation: e.target.checked})}
                  className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
                />
                <span>Enable Auto Moderation</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.spam_filter || false}
                  onChange={(e) => setFormData({...formData, spam_filter: e.target.checked})}
                  className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
                />
                <span>Enable Spam Filter</span>
              </label>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Notification Settings</h4>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.admin_notifications || false}
                  onChange={(e) => setFormData({...formData, admin_notifications: e.target.checked})}
                  className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
                />
                <span>Send Admin Notifications</span>
              </label>
            </div>
          </div>

          <button
            type="submit"
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
          >
            Save Settings
          </button>
        </form>
      </div>
    </div>
  );
};

// =============================================
// Logs Component
// =============================================
const Logs = () => {
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['admin_logs', page, filter],
    queryFn: () => adminApi.getSystemLogs({ page, filter }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Logs</option>
          <option value="error">Errors</option>
          <option value="warning">Warnings</option>
          <option value="info">Info</option>
          <option value="debug">Debug</option>
        </select>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
          Export Logs
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">Time</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Level</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Message</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">User</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {data?.logs?.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition">
                  <td className="px-4 py-2 text-sm">
                    {format(new Date(log.timestamp), 'MMM d, HH:mm:ss')}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${
                      log.level === 'error' ? 'bg-red-100 text-red-700' :
                      log.level === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{log.message}</td>
                  <td className="px-4 py-2 text-sm">{log.user || '-'}</td>
                  <td className="px-4 py-2 text-sm">{log.ip || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Showing {data?.logs?.length || 0} of {data?.total || 0} logs
        </p>
        <div className="flex gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <button
            disabled={!data?.has_more}
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Main Admin App
// =============================================
const AdminApp = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { adminUser, logout } = useAdmin();
  const navigate = useNavigate();

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'users':
        return <UsersManagement />;
      case 'posts':
        return <PostsManagement />;
      case 'moderation':
        return <ModerationQueue />;
      case 'reports':
        return <ReportsManagement />;
      case 'analytics':
        return <Analytics />;
      case 'settings':
        return <Settings />;
      case 'logs':
        return <Logs />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <div className="flex-1 min-h-screen">
          <AdminHeader onLogout={logout} />
          <main className="p-6">
            {renderContent()}
          </main>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Admin Login
// =============================================
const AdminLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAdmin();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/admin');
      toast.success('Welcome back, Admin!');
    } catch (error) {
      toast.error('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
            Admin Login
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Access the admin dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-semibold hover:shadow-lg transition disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
};

// =============================================
// Main App Wrapper
// =============================================
const AdminRoot = () => {
  const { adminUser, loading } = useAdmin();
  const location = useLocation();

  if (loading) {
    return <div className="flex justify-center items-center h-screen"><div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;
  }

  if (!adminUser && location.pathname !== '/admin/login') {
    return <Navigate to="/admin/login" />;
  }

  return (
    <Routes>
      <Route path="/login" element={<AdminLogin />} />
      <Route path="/*" element={adminUser ? <AdminApp /> : <Navigate to="/admin/login" />} />
    </Routes>
  );
};

// =============================================
// Export
// =============================================
const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AdminProvider>
        <BrowserRouter basename="/admin">
          <AdminRoot />
          <Toaster
            position="bottom-center"
            toastOptions={{
              style: {
                background: '#363636',
                color: '#fff',
              },
            }}
          />
        </BrowserRouter>
      </AdminProvider>
    </QueryClientProvider>
  );
};

export default App;
