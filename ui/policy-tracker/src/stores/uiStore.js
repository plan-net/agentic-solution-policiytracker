import { create } from 'zustand'

export const useUIStore = create((set) => ({
  // Sidebar collapsed state
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  // Chat sidebar collapsed state
  chatSidebarCollapsed: false,
  toggleChatSidebar: () => set((state) => ({ chatSidebarCollapsed: !state.chatSidebarCollapsed })),

  // Slide-out panel state
  slideOutPanel: {
    isOpen: false,
    entity: null,
  },

  // Open slide-out panel with entity data
  openSlideOutPanel: (entity) => set({
    slideOutPanel: {
      isOpen: true,
      entity,
    },
  }),

  // Close slide-out panel
  closeSlideOutPanel: () => set({
    slideOutPanel: {
      isOpen: false,
      entity: null,
    },
  }),

  // Recent assessments for sidebar
  recentAssessments: [],
  setRecentAssessments: (assessments) => set({ recentAssessments: assessments }),

  // Loading states
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  // Error handling
  error: null,
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  // Toast notifications
  toasts: [],
  addToast: (toast) => set((state) => ({
    toasts: [...state.toasts, { id: Date.now(), ...toast }],
  })),
  removeToast: (id) => set((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id),
  })),
}))
