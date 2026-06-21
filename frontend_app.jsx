// 2_frontend_app.jsx
/**
 * Instagram Clone - Complete Frontend Application
 * Full UI/UX with all interactions, animations, and real-time updates
 */

import React, { 
  useState, 
  useEffect, 
  useCallback, 
  useRef, 
  useMemo,
  Suspense,
  lazy,
  createContext,
  useContext,
  useReducer
} from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useParams,
  useLocation,
  Link as RouterLink
} from 'react-router-dom';
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery
} from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { motion, AnimatePresence, useScroll, useSpring } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { useSwipeable } from 'react-swipeable';
import { Toaster, toast } from 'react-hot-toast';
import { formatDistanceToNow, format } from 'date-fns';
import { fa, enUS, faIR } from 'date-fns/locale';

// =============================================
// Context Providers
// =============================================
const AuthContext = createContext(null);
const ThemeContext = createContext(null);
const WebSocketContext = createContext(null);
const NotificationContext = createContext(null);

// =============================================
// Custom Hooks
// =============================================
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};

const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) throw new Error('useWebSocket must be used within WebSocketProvider');
  return context;
};

const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) throw new Error('useNotifications must be used within NotificationProvider');
  return context;
};

// =============================================
// API Client
// =============================================
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    this.baseURL = API_BASE;
  }

  setTokens(accessToken, refreshToken) {
    this.token = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens() {
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
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

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (response.status === 401 && this.refreshToken) {
        // Try to refresh token
        const refreshResponse = await fetch(`${this.baseURL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (refreshResponse.ok) {
          const { access_token } = await refreshResponse.json();
          this.setTokens(access_token, this.refreshToken);
          // Retry original request
          return this.request(endpoint, options);
        } else {
          this.clearTokens();
          throw new Error('Session expired');
        }
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Request failed');
      }
      return data;
    } catch (error) {
      throw error;
    }
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

  // Specific API calls
  async login(username, password) {
    const response = await this.post('/auth/login', { username, password });
    this.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async register(username, email, password, fullName) {
    const response = await this.post('/auth/register', {
      username,
      email,
      password,
      full_name: fullName,
    });
    this.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async logout() {
    await this.post('/auth/logout');
    this.clearTokens();
  }

  async getFeed(page = 1, limit = 20) {
    return this.get(`/feed?page=${page}&limit=${limit}`);
  }

  async getPost(postId) {
    return this.get(`/posts/${postId}`);
  }

  async createPost(caption, mediaUrls, mediaType = 'image', location = null, hashtags = null) {
    return this.post('/posts', {
      caption,
      media_urls: mediaUrls,
      media_type: mediaType,
      location,
      hashtags,
    });
  }

  async likePost(postId) {
    return this.post(`/posts/${postId}/like`);
  }

  async unlikePost(postId) {
    return this.delete(`/posts/${postId}/like`);
  }

  async createComment(postId, text, parentId = null) {
    return this.post(`/posts/${postId}/comment`, { text, parent_id: parentId });
  }

  async savePost(postId) {
    return this.post(`/posts/${postId}/save`);
  }

  async unsavePost(postId) {
    return this.delete(`/posts/${postId}/save`);
  }

  async followUser(userId) {
    return this.post(`/users/${userId}/follow`);
  }

  async unfollowUser(userId) {
    return this.delete(`/users/${userId}/follow`);
  }

  async getUserProfile(userId) {
    return this.get(`/users/${userId}`);
  }

  async getMyProfile() {
    return this.get('/users/me');
  }

  async updateProfile(data) {
    return this.put('/users/me', data);
  }

  async searchUsers(query, limit = 20) {
    return this.get(`/users/search?query=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async getStories() {
    return this.get('/stories');
  }

  async getNotifications() {
    return this.get('/notifications');
  }

  async markNotificationRead(notificationId) {
    return this.post(`/notifications/${notificationId}/read`);
  }

  async getTrending(limit = 20) {
    return this.get(`/trending?limit=${limit}`);
  }

  async getFollowers(userId, page = 1, limit = 20) {
    return this.get(`/users/${userId}/followers?page=${page}&limit=${limit}`);
  }

  async getFollowing(userId, page = 1, limit = 20) {
    return this.get(`/users/${userId}/following?page=${page}&limit=${limit}`);
  }
}

const api = new ApiClient();

// =============================================
// Query Client
// =============================================
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 2 * 60 * 1000,
      cacheTime: 5 * 60 * 1000,
    },
    mutations: {
      retry: 0,
    },
  },
});

// =============================================
// Main App Component
// =============================================
const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <WebSocketProvider>
            <NotificationProvider>
              <BrowserRouter>
                <AppRoutes />
              </BrowserRouter>
              <Toaster
                position="bottom-center"
                toastOptions={{
                  duration: 3000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                  success: {
                    duration: 3000,
                    icon: '✅',
                  },
                  error: {
                    duration: 4000,
                    icon: '❌',
                  },
                }}
              />
              <ReactQueryDevtools initialIsOpen={false} />
            </NotificationProvider>
          </WebSocketProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

// =============================================
// Auth Provider
// =============================================
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          const response = await api.get('/users/me');
          setUser(response);
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        api.clearTokens();
      } finally {
        setLoading(false);
        setInitialized(true);
      }
    };
    initAuth();
  }, []);

  const login = async (username, password) => {
    const response = await api.login(username, password);
    setUser(response.user);
    return response;
  };

  const register = async (username, email, password, fullName) => {
    const response = await api.register(username, email, password, fullName);
    setUser(response.user);
    return response;
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  const updateUser = async (data) => {
    const response = await api.updateProfile(data);
    setUser(response);
    return response;
  };

  return (
    <AuthContext.Provider value={{ user, loading, initialized, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
};

// =============================================
// Theme Provider
// =============================================
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved || 'light';
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// =============================================
// WebSocket Provider
// =============================================
const WebSocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const reconnectTimeout = useRef(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback((userId) => {
    if (socket) {
      socket.close();
    }

    const ws = new WebSocket(`${WS_BASE}/${userId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      // Attempt to reconnect
      if (reconnectAttempts.current < 5) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectTimeout.current = setTimeout(() => {
          reconnectAttempts.current++;
          const token = localStorage.getItem('access_token');
          if (token) {
            connect(userId);
          }
        }, delay);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setSocket(ws);

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [socket]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Extract user ID from token or use stored user ID
      const userId = localStorage.getItem('user_id');
      if (userId) {
        connect(userId);
      }
    }

    return () => {
      if (socket) {
        socket.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, []);

  const sendMessage = useCallback((data) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected');
    }
  }, [socket, isConnected]);

  return (
    <WebSocketContext.Provider value={{ socket, isConnected, sendMessage, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

// =============================================
// Notification Provider
// =============================================
const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: api.getNotifications,
    staleTime: 30 * 1000,
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (data) {
      setNotifications(data.notifications || []);
      const unread = (data.notifications || []).filter(n => !n.is_read).length;
      setUnreadCount(unread);
    }
  }, [data]);

  const markAsRead = async (notificationId) => {
    await api.markNotificationRead(notificationId);
    queryClient.invalidateQueries(['notifications']);
  };

  const markAllAsRead = async () => {
    // Implement mark all as read
    await Promise.all(notifications.map(n => markAsRead(n.id)));
  };

  return (
    <NotificationContext.Provider value={{
      notifications,
      unreadCount,
      markAsRead,
      markAllAsRead,
    }}>
      {children}
    </NotificationContext.Provider>
  );
};

// =============================================
// App Routes
// =============================================
const AppRoutes = () => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

      {/* Protected Routes */}
      <Route path="/" element={user ? <ProtectedRoute><Home /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/explore" element={user ? <ProtectedRoute><Explore /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/profile/:username?" element={user ? <ProtectedRoute><Profile /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/post/:postId" element={user ? <ProtectedRoute><PostDetail /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/create" element={user ? <ProtectedRoute><CreatePost /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/messages" element={user ? <ProtectedRoute><Messages /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/notifications" element={user ? <ProtectedRoute><Notifications /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/settings" element={user ? <ProtectedRoute><Settings /></ProtectedRoute> : <Navigate to="/login" />} />
      <Route path="/search" element={user ? <ProtectedRoute><Search /></ProtectedRoute> : <Navigate to="/login" />} />

      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  return children;
};

// =============================================
// Loading Screen
// =============================================
const LoadingScreen = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center">
      <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
      <p className="text-gray-600 dark:text-gray-400">Loading your experience...</p>
      <div className="mt-2 text-sm text-gray-400">Instagram Clone</div>
    </div>
  </div>
);

// =============================================
// Login Page
// =============================================
const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
      toast.success('Welcome back!');
    } catch (error) {
      toast.error(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
            Instagram
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Sign in to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username or email"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              required
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-semibold hover:shadow-lg transition disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Log In'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600 dark:text-gray-400">
            Don't have an account?{' '}
            <RouterLink to="/register" className="text-blue-500 hover:text-blue-600 font-semibold">
              Sign up
            </RouterLink>
          </p>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Register Page
// =============================================
const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    fullName: '',
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(formData.username, formData.email, formData.password, formData.fullName);
      navigate('/');
      toast.success('Account created successfully!');
    } catch (error) {
      toast.error(error.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
            Instagram
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="text"
            placeholder="Full name"
            value={formData.fullName}
            onChange={(e) => setFormData({...formData, fullName: e.target.value})}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({...formData, username: e.target.value})}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-semibold hover:shadow-lg transition disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600 dark:text-gray-400">
            Already have an account?{' '}
            <RouterLink to="/login" className="text-blue-500 hover:text-blue-600 font-semibold">
              Log in
            </RouterLink>
          </p>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Home Page
// =============================================
const Home = () => {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const { ref, inView } = useInView();
  const { user } = useAuth();
  const { sendMessage, lastMessage } = useWebSocket();
  const navigate = useNavigate();

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, refetch } = useInfiniteQuery({
    queryKey: ['feed'],
    queryFn: ({ pageParam = 1 }) => api.getFeed(pageParam),
    getNextPageParam: (lastPage) => lastPage.page < 10 ? lastPage.page + 1 : undefined,
    staleTime: 2 * 60 * 1000,
  });

  useEffect(() => {
    if (data) {
      const allPosts = data.pages.flatMap(p => p.feed || []);
      setFeed(allPosts);
      setHasMore(hasNextPage);
    }
  }, [data, hasNextPage]);

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage]);

  useEffect(() => {
    if (lastMessage) {
      // Handle real-time updates
      if (lastMessage.type === 'new_post') {
        setFeed([lastMessage.post, ...feed]);
        toast.success('New post available!');
      } else if (lastMessage.type === 'new_like') {
        // Update like count
        setFeed(feed.map(p => 
          p.id === lastMessage.post_id 
            ? { ...p, likes_count: p.likes_count + 1 }
            : p
        ));
      }
    }
  }, [lastMessage]);

  const handleLike = async (postId, isLiked) => {
    try {
      if (isLiked) {
        await api.unlikePost(postId);
        setFeed(feed.map(p => 
          p.id === postId 
            ? { ...p, likes_count: p.likes_count - 1, is_liked: false }
            : p
        ));
      } else {
        await api.likePost(postId);
        setFeed(feed.map(p => 
          p.id === postId 
            ? { ...p, likes_count: p.likes_count + 1, is_liked: true }
            : p
        ));
        // Send WebSocket notification
        sendMessage({
          type: 'like',
          post_id: postId,
        });
      }
    } catch (error) {
      toast.error('Failed to like post');
    }
  };

  const handleComment = async (postId, text) => {
    try {
      const response = await api.createComment(postId, text);
      setFeed(feed.map(p => 
        p.id === postId 
          ? { ...p, comments_count: p.comments_count + 1 }
          : p
      ));
      toast.success('Comment added!');
    } catch (error) {
      toast.error('Failed to add comment');
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      {/* Stories */}
      <StoriesBar />

      {/* Feed */}
      <div className="space-y-6">
        {feed.map((post, index) => (
          <FeedPost
            key={post.id}
            post={post}
            onLike={handleLike}
            onComment={handleComment}
            onNavigate={() => navigate(`/post/${post.id}`)}
          />
        ))}

        {/* Load more trigger */}
        <div ref={ref} className="flex justify-center py-4">
          {isFetchingNextPage ? (
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-500 dark:text-gray-400">Loading more...</span>
            </div>
          ) : feed.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              <p className="text-4xl mb-2">📸</p>
              <p className="text-lg font-semibold">No posts yet</p>
              <p className="text-sm">Follow people to see their posts</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Stories Bar
// =============================================
const StoriesBar = () => {
  const { data } = useQuery({
    queryKey: ['stories'],
    queryFn: api.getStories,
    staleTime: 60 * 1000,
    refetchInterval: 30000,
  });

  const stories = data?.stories || [];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 mb-6 overflow-x-auto">
      <div className="flex gap-4">
        {/* Your story */}
        <div className="flex flex-col items-center cursor-pointer group">
          <div className="w-16 h-16 rounded-full ring-2 ring-gray-300 dark:ring-gray-600 group-hover:ring-blue-500 transition p-0.5">
            <img
              src="https://via.placeholder.com/64"
              alt="Your story"
              className="w-full h-full rounded-full object-cover"
            />
          </div>
          <span className="text-xs mt-1 text-gray-600 dark:text-gray-400">Your story</span>
        </div>

        {/* Other stories */}
        {stories.map((story) => (
          <div key={story.id} className="flex flex-col items-center cursor-pointer group">
            <div className="w-16 h-16 rounded-full ring-2 ring-gradient-to-r from-pink-500 to-purple-500 group-hover:ring-blue-500 transition p-0.5">
              <img
                src={story.media_url || 'https://via.placeholder.com/64'}
                alt="Story"
                className="w-full h-full rounded-full object-cover"
              />
            </div>
            <span className="text-xs mt-1 text-gray-600 dark:text-gray-400 truncate max-w-[64px]">
              {story.user?.username || 'User'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// =============================================
// Feed Post Component
// =============================================
const FeedPost = ({ post, onLike, onComment, onNavigate }) => {
  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likesCount, setLikesCount] = useState(post.likes_count || 0);
  const [showComments, setShowComments] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentMediaIndex, setCurrentMediaIndex] = useState(0);
  const postRef = useRef();

  const handleLike = () => {
    setIsLiked(!isLiked);
    setLikesCount(prev => isLiked ? prev - 1 : prev + 1);
    onLike(post.id, isLiked);
  };

  const handleCommentSubmit = (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    onComment(post.id, commentText);
    setCommentText('');
  };

  const mediaUrls = post.media_urls || [];
  const isCarousel = mediaUrls.length > 1;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <img
            src={post.user?.profile_pic || 'https://via.placeholder.com/40'}
            alt={post.user?.username}
            className="w-10 h-10 rounded-full object-cover ring-2 ring-gray-300 dark:ring-gray-600"
          />
          <div>
            <span className="font-semibold hover:underline cursor-pointer">
              {post.user?.username || 'Unknown'}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 block">
              {formatDistanceToNow(new Date(post.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition">
          <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>
      </div>

      {/* Media */}
      <div className="relative bg-black" onClick={onNavigate}>
        {isCarousel ? (
          <div className="relative">
            <img
              src={mediaUrls[currentMediaIndex]}
              alt="Post"
              className="w-full max-h-[600px] object-contain"
            />
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-1.5">
              {mediaUrls.map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full transition ${
                    i === currentMediaIndex ? 'bg-white w-4' : 'bg-white/50'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setCurrentMediaIndex(prev => prev === 0 ? mediaUrls.length - 1 : prev - 1); }}
              className="absolute left-2 top-1/2 transform -translate-y-1/2 w-8 h-8 bg-black/50 rounded-full flex items-center justify-center text-white hover:bg-black/70 transition"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setCurrentMediaIndex(prev => prev === mediaUrls.length - 1 ? 0 : prev + 1); }}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 w-8 h-8 bg-black/50 rounded-full flex items-center justify-center text-white hover:bg-black/70 transition"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        ) : (
          <img
            src={mediaUrls[0] || 'https://via.placeholder.com/600x400'}
            alt="Post"
            className="w-full max-h-[600px] object-contain"
          />
        )}
      </div>

      {/* Actions */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={handleLike} className="group">
              <span className="text-2xl transition group-hover:scale-110">
                {isLiked ? '❤️' : '🤍'}
              </span>
            </button>
            <button onClick={() => setShowComments(!showComments)} className="text-2xl hover:scale-110 transition">
              💬
            </button>
            <button className="text-2xl hover:scale-110 transition">📤</button>
          </div>
          <button className="text-2xl hover:scale-110 transition">🔖</button>
        </div>

        <div className="mt-2">
          <span className="font-semibold cursor-pointer" onClick={onNavigate}>
            {likesCount.toLocaleString()} likes
          </span>
        </div>

        {/* Caption */}
        <div className="mt-1">
          <span className="font-semibold">{post.user?.username}</span>
          <span className="ml-2">
            {isExpanded ? post.caption : post.caption?.slice(0, 150)}
            {post.caption?.length > 150 && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 ml-2 text-sm"
              >
                {isExpanded ? 'less' : 'more'}
              </button>
            )}
          </span>
        </div>

        {/* Hashtags */}
        {post.hashtags?.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {post.hashtags.map(tag => (
              <span key={tag} className="text-blue-500 hover:underline text-sm cursor-pointer">
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Comments */}
        {post.comments_count > 0 && (
          <button
            onClick={() => setShowComments(!showComments)}
            className="text-gray-500 dark:text-gray-400 text-sm mt-1 hover:text-gray-700 dark:hover:text-gray-300"
          >
            View all {post.comments_count.toLocaleString()} comments
          </button>
        )}

        {/* Comment Input */}
        <form onSubmit={handleCommentSubmit} className="mt-3 border-t dark:border-gray-700 pt-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add a comment..."
              className="flex-1 outline-none text-sm bg-transparent placeholder-gray-500 dark:placeholder-gray-400"
            />
            <button
              type="submit"
              disabled={!commentText.trim()}
              className="text-blue-500 font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Post
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// =============================================
// Profile Page
// =============================================
const Profile = () => {
  const { username } = useParams();
  const { user: currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('posts');
  const [isFollowing, setIsFollowing] = useState(false);
  const navigate = useNavigate();

  const isOwnProfile = !username || username === currentUser?.username;

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        let userId;
        if (isOwnProfile) {
          const me = await api.getMyProfile();
          userId = me.id;
          setProfile(me);
        } else {
          // Search user by username
          const searchResults = await api.searchUsers(username);
          const found = searchResults.results.find(u => u.username === username);
          if (found) {
            const userData = await api.getUserProfile(found.id);
            setProfile(userData);
            userId = found.id;
          } else {
            toast.error('User not found');
            navigate('/');
            return;
          }
        }
        // Check if following
        if (userId) {
          // Implement follow check
        }
      } catch (error) {
        toast.error('Failed to load profile');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [username, isOwnProfile, navigate]);

  const handleFollow = async () => {
    if (!profile) return;
    try {
      if (isFollowing) {
        await api.unfollowUser(profile.id);
        setIsFollowing(false);
        setProfile({...profile, follower_count: profile.follower_count - 1});
        toast.success('Unfollowed');
      } else {
        await api.followUser(profile.id);
        setIsFollowing(true);
        setProfile({...profile, follower_count: profile.follower_count + 1});
        toast.success('Followed');
      }
    } catch (error) {
      toast.error('Action failed');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Profile Header */}
      <div className="flex flex-col md:flex-row items-center gap-8">
        <div className="w-32 h-32 md:w-40 md:h-40 rounded-full overflow-hidden ring-4 ring-gray-200 dark:ring-gray-700 flex-shrink-0">
          <img
            src={profile.profile_pic || 'https://via.placeholder.com/160'}
            alt={profile.username}
            className="w-full h-full object-cover"
          />
        </div>

        <div className="flex-1 text-center md:text-left">
          <div className="flex flex-col md:flex-row items-center gap-4 mb-4">
            <h2 className="text-2xl font-bold">{profile.username}</h2>
            <div className="flex gap-2">
              {isOwnProfile ? (
                <button
                  onClick={() => navigate('/settings')}
                  className="px-4 py-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition text-sm font-semibold"
                >
                  Edit Profile
                </button>
              ) : (
                <button
                  onClick={handleFollow}
                  className={`px-6 py-1.5 rounded-lg transition text-sm font-semibold ${
                    isFollowing
                      ? 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'
                      : 'bg-blue-500 hover:bg-blue-600 text-white'
                  }`}
                >
                  {isFollowing ? 'Following' : 'Follow'}
                </button>
              )}
            </div>
          </div>

          <div className="flex justify-center md:justify-start gap-8 mb-4">
            <div>
              <span className="font-semibold">{profile.post_count || 0}</span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">posts</span>
            </div>
            <div>
              <span className="font-semibold">{profile.follower_count || 0}</span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">followers</span>
            </div>
            <div>
              <span className="font-semibold">{profile.following_count || 0}</span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">following</span>
            </div>
          </div>

          <div>
            <p className="font-semibold">{profile.full_name}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">{profile.bio}</p>
            {profile.website && (
              <a
                href={profile.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline text-sm"
              >
                {profile.website}
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-t dark:border-gray-700 mt-8">
        <div className="flex justify-center gap-12">
          <button
            onClick={() => setActiveTab('posts')}
            className={`py-3 border-t-2 transition ${
              activeTab === 'posts'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-500 dark:text-gray-400'
            }`}
          >
            Posts
          </button>
          <button
            onClick={() => setActiveTab('saved')}
            className={`py-3 border-t-2 transition ${
              activeTab === 'saved'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-500 dark:text-gray-400'
            }`}
          >
            Saved
          </button>
          <button
            onClick={() => setActiveTab('tagged')}
            className={`py-3 border-t-2 transition ${
              activeTab === 'tagged'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-500 dark:text-gray-400'
            }`}
          >
            Tagged
          </button>
        </div>
      </div>

      {/* Posts Grid */}
      <div className="mt-4 grid grid-cols-3 gap-1 md:gap-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
            <img
              src="https://via.placeholder.com/300"
              alt="Post"
              className="w-full h-full object-cover hover:scale-105 transition duration-300"
            />
          </div>
        ))}
      </div>
    </div>
  );
};

// =============================================
// Explore Page
// =============================================
const Explore = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const { data: trending } = useQuery({
    queryKey: ['trending'],
    queryFn: api.getTrending,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const search = async () => {
      if (searchQuery.length < 2) {
        setSearchResults([]);
        return;
      }
      setIsSearching(true);
      try {
        const results = await api.searchUsers(searchQuery);
        setSearchResults(results.results || []);
      } catch (error) {
        toast.error('Search failed');
      } finally {
        setIsSearching(false);
      }
    };
    const debounce = setTimeout(search, 500);
    return () => clearTimeout(debounce);
  }, [searchQuery]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-4">
      {/* Search Bar */}
      <div className="max-w-md mx-auto mb-8">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search users..."
            className="w-full px-4 py-3 pl-12 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
          />
          <svg
            className="absolute left-4 top-3.5 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Search Results */}
      {searchQuery.length >= 2 && (
        <div className="space-y-2 mb-8">
          {isSearching ? (
            <div className="flex justify-center py-8">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map(user => (
              <div key={user.id} className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-xl hover:shadow-md transition">
                <div className="flex items-center gap-3">
                  <img
                    src={user.profile_pic || 'https://via.placeholder.com/40'}
                    alt={user.username}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                  <div>
                    <p className="font-semibold">{user.username}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{user.full_name}</p>
                  </div>
                </div>
                <button className="px-4 py-1.5 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 transition">
                  Follow
                </button>
              </div>
            ))
          ) : (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              No users found
            </div>
          )}
        </div>
      )}

      {/* Trending Posts */}
      <div>
        <h2 className="text-xl font-bold mb-4">Trending</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {trending?.trending?.map((post, i) => (
            <div key={post.id} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden relative group">
              <img
                src={post.media_urls?.[0] || 'https://via.placeholder.com/300'}
                alt="Trending"
                className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
              />
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-4">
                <span className="text-white font-semibold flex items-center gap-1">
                  ❤️ {post.likes_count || 0}
                </span>
                <span className="text-white font-semibold flex items-center gap-1">
                  💬 {post.comments_count || 0}
                </span>
              </div>
              <div className="absolute top-2 left-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                #{i + 1}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Create Post Page
// =============================================
const CreatePost = () => {
  const [caption, setCaption] = useState('');
  const [mediaFiles, setMediaFiles] = useState([]);
  const [mediaUrls, setMediaUrls] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [location, setLocation] = useState('');
  const [hashtags, setHashtags] = useState('');
  const navigate = useNavigate();
  const fileInputRef = useRef();

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setMediaFiles(files);
    // Preview URLs
    const urls = files.map(file => URL.createObjectURL(file));
    setMediaUrls(urls);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (mediaFiles.length === 0) {
      toast.error('Please select at least one media');
      return;
    }

    setUploading(true);
    try {
      // Upload files
      const uploadedUrls = [];
      for (const file of mediaFiles) {
        const formData = new FormData();
        formData.append('file', file);
        // Upload to server
        // const response = await api.uploadMedia(formData);
        // uploadedUrls.push(response.url);
        uploadedUrls.push(URL.createObjectURL(file)); // Temporary
      }

      const hashtagList = hashtags.split(',').map(t => t.trim()).filter(t => t);
      await api.createPost(caption, uploadedUrls, 'image', location, hashtagList);
      toast.success('Post created successfully!');
      navigate('/');
    } catch (error) {
      toast.error('Failed to create post');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-6">Create New Post</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Media Upload */}
          <div>
            <label className="block text-sm font-semibold mb-2">Media</label>
            <div
              className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
              {mediaUrls.length > 0 ? (
                <div className="grid grid-cols-3 gap-2">
                  {mediaUrls.map((url, i) => (
                    <div key={i} className="aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
                      <img src={url} alt={`Preview ${i}`} className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              ) : (
                <div>
                  <div className="text-4xl mb-2">📸</div>
                  <p className="text-gray-500 dark:text-gray-400">Click to select images or videos</p>
                  <p className="text-sm text-gray-400 mt-1">Max 10 files</p>
                </div>
              )}
            </div>
          </div>

          {/* Caption */}
          <div>
            <label className="block text-sm font-semibold mb-2">Caption</label>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Write a caption..."
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition resize-none"
              rows={4}
            />
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-semibold mb-2">Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Add location..."
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          {/* Hashtags */}
          <div>
            <label className="block text-sm font-semibold mb-2">Hashtags</label>
            <input
              type="text"
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="Separate with commas (e.g., instagram, photo)"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={uploading || mediaFiles.length === 0}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-semibold hover:shadow-lg transition disabled:opacity-50"
          >
            {uploading ? 'Creating post...' : 'Share Post'}
          </button>
        </form>
      </div>
    </div>
  );
};

// =============================================
// Notifications Page
// =============================================
const Notifications = () => {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Notifications</h1>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-sm text-blue-500 font-semibold hover:text-blue-600 transition"
            >
              Mark all as read
            </button>
          )}
        </div>

        <div className="space-y-2">
          {notifications.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              <p className="text-4xl mb-2">🔔</p>
              <p>No notifications yet</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.id}
                className={`flex items-start gap-3 p-3 rounded-lg transition ${
                  notification.is_read
                    ? 'hover:bg-gray-50 dark:hover:bg-gray-700'
                    : 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                }`}
                onClick={() => markAsRead(notification.id)}
              >
                <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                  {notification.type === 'like' && '❤️'}
                  {notification.type === 'comment' && '💬'}
                  {notification.type === 'follow' && '👤'}
                  {notification.type === 'mention' && '@'}
                </div>
                <div className="flex-1">
                  <p className="text-sm">{notification.message}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                  </p>
                </div>
                {!notification.is_read && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-2" />
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

// =============================================
// Messages Page
// =============================================
const Messages = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState('');
  const { sendMessage, lastMessage } = useWebSocket();

  // Dummy conversations
  useEffect(() => {
    setConversations([
      { id: 1, username: 'alice', last_message: 'Hey! How are you?', time: '2h ago' },
      { id: 2, username: 'bob', last_message: 'Check out my new post!', time: '5h ago' },
      { id: 3, username: 'charlie', last_message: 'See you tomorrow!', time: '1d ago' },
    ]);
  }, []);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!messageText.trim() || !selectedConversation) return;

    const newMessage = {
      id: Date.now(),
      text: messageText,
      sender: 'me',
      time: new Date().toISOString(),
    };
    setMessages([...messages, newMessage]);
    sendMessage({
      type: 'message',
      receiver_id: selectedConversation.id,
      message: messageText,
    });
    setMessageText('');
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="flex h-[600px]">
          {/* Conversations List */}
          <div className="w-1/3 border-r dark:border-gray-700">
            <div className="p-4 border-b dark:border-gray-700">
              <h2 className="text-xl font-bold">Messages</h2>
            </div>
            <div className="overflow-y-auto h-[calc(100%-60px)]">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConversation(conv)}
                  className={`w-full p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition ${
                    selectedConversation?.id === conv.id
                      ? 'bg-gray-50 dark:bg-gray-700'
                      : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                      {conv.username[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold">{conv.username}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{conv.last_message}</p>
                    </div>
                    <span className="text-xs text-gray-400">{conv.time}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Chat Window */}
          <div className="w-2/3 flex flex-col">
            {selectedConversation ? (
              <>
                <div className="p-4 border-b dark:border-gray-700 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                    {selectedConversation.username[0].toUpperCase()}
                  </div>
                  <span className="font-semibold">{selectedConversation.username}</span>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.sender === 'me' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[70%] p-3 rounded-2xl ${
                          msg.sender === 'me'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 dark:bg-gray-700'
                        }`}
                      >
                        <p className="text-sm">{msg.text}</p>
                        <span className="text-xs opacity-75 mt-1 block">
                          {formatDistanceToNow(new Date(msg.time), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleSendMessage} className="p-4 border-t dark:border-gray-700">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      placeholder="Type a message..."
                      className="flex-1 px-4 py-2 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                    />
                    <button
                      type="submit"
                      disabled={!messageText.trim()}
                      className="px-6 py-2 bg-blue-500 text-white rounded-full font-semibold hover:bg-blue-600 transition disabled:opacity-50"
                    >
                      Send
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <p className="text-4xl mb-2">💬</p>
                  <p>Select a conversation</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// =============================================
// Settings Page
// =============================================
const Settings = () => {
  const { user, updateUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        bio: user.bio || '',
        website: user.website || '',
        location: user.location || '',
        is_private: user.is_private || false,
      });
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await updateUser(formData);
      toast.success('Profile updated successfully!');
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-2">Full Name</label>
            <input
              type="text"
              value={formData.full_name || ''}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-2">Bio</label>
            <textarea
              value={formData.bio || ''}
              onChange={(e) => setFormData({...formData, bio: e.target.value})}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition resize-none"
              rows={4}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-2">Website</label>
            <input
              type="url"
              value={formData.website || ''}
              onChange={(e) => setFormData({...formData, website: e.target.value})}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-2">Location</label>
            <input
              type="text"
              value={formData.location || ''}
              onChange={(e) => setFormData({...formData, location: e.target.value})}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={formData.is_private || false}
              onChange={(e) => setFormData({...formData, is_private: e.target.checked})}
              className="w-5 h-5 text-blue-500 rounded focus:ring-blue-500"
            />
            <label className="text-sm font-medium">Private Account</label>
          </div>

          <div className="pt-4 border-t dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold">Dark Mode</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Toggle dark theme</p>
              </div>
              <button
                type="button"
                onClick={toggleTheme}
                className="w-12 h-6 bg-gray-300 dark:bg-gray-600 rounded-full relative transition"
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition ${
                    theme === 'dark' ? 'left-6' : 'left-0.5'
                  }`}
                />
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
};

// =============================================
// Post Detail Page
// =============================================
const PostDetail = () => {
  const { postId } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPost = async () => {
      try {
        const data = await api.getPost(postId);
        setPost(data);
      } catch (error) {
        toast.error('Post not found');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    fetchPost();
  }, [postId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!post) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-4">
      <button onClick={() => navigate(-1)} className="mb-4 text-blue-500 hover:text-blue-600">
        ← Back
      </button>
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <FeedPost
          post={post}
          onLike={() => {}}
          onComment={() => {}}
          onNavigate={() => {}}
        />
      </div>
    </div>
  );
};

// =============================================
// Search Page
// =============================================
const Search = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const search = async () => {
      if (query.length < 2) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const data = await api.searchUsers(query);
        setResults(data.results || []);
      } catch (error) {
        toast.error('Search failed');
      } finally {
        setLoading(false);
      }
    };
    const debounce = setTimeout(search, 500);
    return () => clearTimeout(debounce);
  }, [query]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <h1 className="text-2xl font-bold mb-6">Search</h1>

        <div className="relative mb-6">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search users..."
            className="w-full px-4 py-3 pl-12 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
          />
          <svg
            className="absolute left-4 top-3.5 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : results.length > 0 ? (
          <div className="space-y-2">
            {results.map(user => (
              <div key={user.id} className="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition">
                <div className="flex items-center gap-3">
                  <img
                    src={user.profile_pic || 'https://via.placeholder.com/40'}
                    alt={user.username}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                  <div>
                    <p className="font-semibold">{user.username}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{user.full_name}</p>
                  </div>
                </div>
                <button className="px-4 py-1.5 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 transition">
                  Follow
                </button>
              </div>
            ))}
          </div>
        ) : query.length >= 2 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            No users found
          </div>
        ) : null}
      </div>
    </div>
  );
};

// =============================================
// Navigation Bar
// =============================================
const NavigationBar = () => {
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { icon: '🏠', path: '/' },
    { icon: '🔍', path: '/explore' },
    { icon: '📸', path: '/create' },
    { icon: '💬', path: '/messages' },
    { icon: '🔔', path: '/notifications', badge: unreadCount },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <span className="text-2xl">📸</span>
            <span className="text-xl font-bold bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent hidden sm:inline">
              Instagram
            </span>
          </div>

          {/* Search */}
          <div className="hidden md:block flex-1 max-w-sm mx-8">
            <input
              type="text"
              placeholder="Search"
              className="w-full px-4 py-2 rounded-full bg-gray-100 dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition text-sm"
              onFocus={() => navigate('/search')}
            />
          </div>

          {/* Nav Items */}
          <div className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition relative ${
                  location.pathname === item.path ? 'text-blue-500' : ''
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                {item.badge > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                    {item.badge > 9 ? '9+' : item.badge}
                  </span>
                )}
              </button>
            ))}

            {/* Profile */}
            <button
              onClick={() => navigate(`/profile/${user?.username}`)}
              className="p-1 rounded-full hover:ring-2 hover:ring-blue-500 transition"
            >
              <img
                src={user?.profile_pic || 'https://via.placeholder.com/32'}
                alt={user?.username}
                className="w-8 h-8 rounded-full object-cover"
              />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

// =============================================
// Mobile Navigation
// =============================================
const MobileNavigation = () => {
  const { unreadCount } = useNotifications();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { icon: '🏠', path: '/' },
    { icon: '🔍', path: '/explore' },
    { icon: '📸', path: '/create' },
    { icon: '💬', path: '/messages' },
    { icon: '🔔', path: '/notifications', badge: unreadCount },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-t border-gray-200 dark:border-gray-700 md:hidden">
      <div className="flex justify-around items-center h-16">
        {navItems.map((item) => (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            className="relative p-2 flex-1 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <span className="text-2xl">{item.icon}</span>
            {item.badge > 0 && (
              <span className="absolute top-1 right-1/4 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {item.badge > 9 ? '9+' : item.badge}
              </span>
            )}
          </button>
        ))}
      </div>
    </nav>
  );
};

// =============================================
// Export
// =============================================
export default App;
