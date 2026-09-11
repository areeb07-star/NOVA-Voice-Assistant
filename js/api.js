/* ============================================
   NOVA - API Layer (FIXED)
   ============================================ */

const API_BASE_URL = "http://127.0.0.1:8000/api";

const MOCK_DELAY = 300; // faster for demo

/* ---------- Mock Data ---------- */
const mockData = {
  user: {
    id: 1,
    fullName: "Arjun Sharma",
    username: "arjun_dev",
    email: "arjun@example.com",
    avatar: null,
    joined: "2024-01-15"
  },

  reminders: [
    { id: 1, title: "Study Python", time: "Today · 7:00 PM", status: "pending", priority: "high", category: "study" },
    { id: 2, title: "Submit assignment", time: "Tomorrow · 11:59 PM", status: "pending", priority: "high", category: "study" },
    { id: 3, title: "Team meeting", time: "Friday · 3:00 PM", status: "pending", priority: "medium", category: "work" },
    { id: 4, title: "Gym session", time: "Today · 6:00 AM", status: "completed", priority: "low", category: "health" },
    { id: 5, title: "Call parents", time: "Sunday · 10:00 AM", status: "pending", priority: "medium", category: "personal" }
  ],

  notes: [
    { id: 1, title: "Python Functions", content: "Functions are reusable blocks of code that perform specific tasks. They help organize code and avoid repetition.", tags: ["Python", "Study", "Important"], pinned: true, date: "2024-03-10" },
    { id: 2, title: "Django API Notes", content: "Django REST Framework serializers convert complex data to native Python. Views handle request/response logic.", tags: ["Django", "API", "Backend"], pinned: false, date: "2024-03-09" },
    { id: 3, title: "Project Ideas", content: "1. AI-powered study assistant\n2. Smart expense tracker\n3. Voice-controlled home automation", tags: ["Ideas", "Projects"], pinned: true, date: "2024-03-08" },
    { id: 4, title: "SQL Joins Cheatsheet", content: "INNER JOIN: matching rows in both tables\nLEFT JOIN: all rows from left + matches", tags: ["SQL", "Database", "Study"], pinned: false, date: "2024-03-07" }
  ],

  shopping: [
    { id: 1, name: "Milk", quantity: 2, category: "Groceries", purchased: false },
    { id: 2, name: "Notebook", quantity: 1, category: "Stationery", purchased: false },
    { id: 3, name: "Pens", quantity: 5, category: "Stationery", purchased: true },
    { id: 4, name: "Headphones", quantity: 1, category: "Electronics", purchased: false },
    { id: 5, name: "Bread", quantity: 1, category: "Groceries", purchased: true },
    { id: 6, name: "USB Cable", quantity: 2, category: "Electronics", purchased: false },
    { id: 7, name: "Water Bottle", quantity: 1, category: "Other", purchased: true },
    { id: 8, name: "Sticky Notes", quantity: 3, category: "Stationery", purchased: false }
  ],

  expenses: [
    { id: 1, title: "Lunch at canteen", amount: 150, category: "Food", date: "2024-03-10" },
    { id: 2, title: "Bus fare", amount: 50, category: "Travel", date: "2024-03-10" },
    { id: 3, title: "Python course", amount: 499, category: "Education", date: "2024-03-09" },
    { id: 4, title: "New notebook", amount: 120, category: "Education", date: "2024-03-09" },
    { id: 5, title: "Groceries", amount: 850, category: "Food", date: "2024-03-08" },
    { id: 6, title: "Movie ticket", amount: 300, category: "Other", date: "2024-03-08" },
    { id: 7, title: "Phone bill", amount: 599, category: "Bills", date: "2024-03-07" },
    { id: 8, title: "T-shirt", amount: 699, category: "Shopping", date: "2024-03-06" },
    { id: 9, title: "Auto fare", amount: 80, category: "Travel", date: "2024-03-06" },
    { id: 10, title: "Dinner", amount: 450, category: "Food", date: "2024-03-05" }
  ],

  studyPlans: [
    {
      id: 1, subject: "Python", examDate: "2024-04-15",
      topics: ["Basics", "Functions", "OOP", "Revision", "Mock Test"],
      dailyTime: "2 hours", progress: 68,
      timeline: [
        { day: "MON", topic: "Python Basics", status: "completed" },
        { day: "TUE", topic: "Functions", status: "completed" },
        { day: "WED", topic: "OOP", status: "today" },
        { day: "THU", topic: "Revision", status: "upcoming" },
        { day: "FRI", topic: "Mock Test", status: "upcoming" }
      ]
    },
    {
      id: 2, subject: "Django", examDate: "2024-04-22",
      topics: ["Models", "Views", "Templates", "REST API", "Deployment"],
      dailyTime: "1.5 hours", progress: 35,
      timeline: [
        { day: "MON", topic: "Models", status: "completed" },
        { day: "TUE", topic: "Views", status: "today" },
        { day: "WED", topic: "Templates", status: "upcoming" },
        { day: "THU", topic: "REST API", status: "upcoming" },
        { day: "FRI", topic: "Deployment", status: "upcoming" }
      ]
    },
    {
      id: 3, subject: "SQL", examDate: "2024-04-10",
      topics: ["SELECT", "JOINs", "Indexing", "Optimization"],
      dailyTime: "1 hour", progress: 82,
      timeline: [
        { day: "MON", topic: "SELECT", status: "completed" },
        { day: "TUE", topic: "JOINs", status: "completed" },
        { day: "WED", topic: "Indexing", status: "completed" },
        { day: "THU", topic: "Optimization", status: "today" },
        { day: "FRI", topic: "Review", status: "upcoming" }
      ]
    }
  ],

  goals: [
    { id: 1, title: "Complete Python Course", progress: 72, category: "Education", target: "2024-04-30", color: "cyan" },
    { id: 2, title: "Build NOVA", progress: 45, category: "Project", target: "2024-05-15", color: "violet" },
    { id: 3, title: "Get Internship", progress: 30, category: "Career", target: "2024-06-01", color: "pink" },
    { id: 4, title: "Read 12 Books", progress: 58, category: "Personal", target: "2024-12-31", color: "green" }
  ],

  dashboardStats: {
    remindersToday: 3,
    notesCount: 12,
    shoppingItems: 5,
    studyTasks: 4,
    goalProgress: 72
  },

  chatHistory: [
    { id: 1, sender: "user", text: "Remind me to study Python at 7 PM.", time: "6:45 PM" },
    { id: 2, sender: "nova", text: "Absolutely! ✨\n\nI've created a reminder for Python study at 7:00 PM.", time: "6:45 PM" }
  ]
};

/* ---------- Simulator ---------- */
function simulateRequest(data, delay = MOCK_DELAY) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ success: true, data: JSON.parse(JSON.stringify(data)) });
    }, delay);
  });
}

/* ---------- Auth ---------- */
async function loginUser(email, password) {
  console.log("[NOVA API] loginUser called:", email);
  return simulateRequest({
    token: "mock-jwt-token-" + Date.now(),
    user: { ...mockData.user, email }
  });
}

async function registerUser(userData) {
  console.log("[NOVA API] registerUser called:", userData.email);
  return simulateRequest({
    token: "mock-jwt-token-" + Date.now(),
    user: { ...mockData.user, ...userData }
  });
}

/* ---------- Reminders ---------- */
async function getReminders() { return simulateRequest(mockData.reminders); }
async function createReminder(r) {
  const n = { id: Date.now(), status: "pending", priority: "medium", category: "other", ...r };
  mockData.reminders.unshift(n);
  return simulateRequest(n);
}
async function updateReminder(id, updates) {
  const i = mockData.reminders.findIndex(r => r.id === id);
  if (i !== -1) {
    mockData.reminders[i] = { ...mockData.reminders[i], ...updates };
    return simulateRequest(mockData.reminders[i]);
  }
  return simulateRequest(null);
}
async function deleteReminder(id) {
  mockData.reminders = mockData.reminders.filter(r => r.id !== id);
  return simulateRequest({ id });
}

/* ---------- Notes ---------- */
async function getNotes() { return simulateRequest(mockData.notes); }
async function createNote(n) {
  const note = { id: Date.now(), tags: [], pinned: false, date: new Date().toISOString().split("T")[0], ...n };
  mockData.notes.unshift(note);
  return simulateRequest(note);
}
async function updateNote(id, updates) {
  const i = mockData.notes.findIndex(n => n.id === id);
  if (i !== -1) {
    mockData.notes[i] = { ...mockData.notes[i], ...updates };
    return simulateRequest(mockData.notes[i]);
  }
  return simulateRequest(null);
}
async function deleteNote(id) {
  mockData.notes = mockData.notes.filter(n => n.id !== id);
  return simulateRequest({ id });
}

/* ---------- Shopping ---------- */
async function getShoppingItems() { return simulateRequest(mockData.shopping); }
async function createShoppingItem(item) {
  const n = { id: Date.now(), quantity: 1, category: "Other", purchased: false, ...item };
  mockData.shopping.unshift(n);
  return simulateRequest(n);
}
async function updateShoppingItem(id, updates) {
  const i = mockData.shopping.findIndex(x => x.id === id);
  if (i !== -1) {
    mockData.shopping[i] = { ...mockData.shopping[i], ...updates };
    return simulateRequest(mockData.shopping[i]);
  }
  return simulateRequest(null);
}
async function deleteShoppingItem(id) {
  mockData.shopping = mockData.shopping.filter(x => x.id !== id);
  return simulateRequest({ id });
}

/* ---------- Expenses ---------- */
async function getExpenses() { return simulateRequest(mockData.expenses); }
async function createExpense(e) {
  const n = { id: Date.now(), date: new Date().toISOString().split("T")[0], ...e };
  mockData.expenses.unshift(n);
  return simulateRequest(n);
}
async function updateExpense(id, updates) {
  const i = mockData.expenses.findIndex(x => x.id === id);
  if (i !== -1) {
    mockData.expenses[i] = { ...mockData.expenses[i], ...updates };
    return simulateRequest(mockData.expenses[i]);
  }
  return simulateRequest(null);
}
async function deleteExpense(id) {
  mockData.expenses = mockData.expenses.filter(x => x.id !== id);
  return simulateRequest({ id });
}

/* ---------- Study Plans ---------- */
async function getStudyPlans() { return simulateRequest(mockData.studyPlans); }
async function createStudyPlan(plan) {
  const n = { id: Date.now(), progress: 0, timeline: [], ...plan };
  mockData.studyPlans.unshift(n);
  return simulateRequest(n);
}

/* ---------- Goals ---------- */
async function getGoals() { return simulateRequest(mockData.goals); }
async function createGoal(goal) {
  const n = { id: Date.now(), progress: 0, color: "cyan", ...goal };
  mockData.goals.unshift(n);
  return simulateRequest(n);
}

/* ---------- Assistant ---------- */
async function sendAssistantMessage(message) {
  const responses = [
    "I've noted that down for you. ✨",
    "Got it! I'll remember that.",
    "Consider it done! 🚀",
    "Absolutely! I've added that to your list.",
    "I'm on it! Anything else you need?",
    "That's a great idea. I've saved it for you.",
    "Done! I've updated your information.",
    "I understand. Let me help you with that."
  ];
  const randomResponse = responses[Math.floor(Math.random() * responses.length)];
  return simulateRequest({
    sender: "nova",
    text: randomResponse,
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }, 1000);
}

/* ---------- Dashboard ---------- */
async function getDashboardStats() { return simulateRequest(mockData.dashboardStats); }
async function getChatHistory() { return simulateRequest(mockData.chatHistory); }

window.NOVA_MOCK = mockData;