import { createBrowserRouter } from "react-router-dom"
import { RoleGuard } from "@/auth/role-guard"
import { AdminLayout } from "@/components/layout/admin-layout"
import { AppLayout } from "@/components/layout/app-layout"
import { ActivityPage } from "@/pages/activity-page"
import { AdminAuditPage } from "@/pages/admin-audit-page"
import { AdminDashboardPage } from "@/pages/admin-dashboard-page"
import { AdminEvaluationsPage } from "@/pages/admin-evaluations-page"
import { AdminSystemPage } from "@/pages/admin-system-page"
import { AdminUsersPage } from "@/pages/admin-users-page"
import { AnalyticsPage } from "@/pages/analytics-page"
import { AppDashboardPage } from "@/pages/app-dashboard-page"
import { EvaluationPage } from "@/pages/evaluation-page"
import { ForgotPasswordPage } from "@/pages/forgot-password-page"
import { HomePage } from "@/pages/home-page"
import { OnboardingPage } from "@/pages/onboarding-page"
import { PortfolioPage } from "@/pages/portfolio-page"
import { RebalanceReviewPage } from "@/pages/rebalance-review-page"
import { SettingsPage } from "@/pages/settings-page"
import { SignInPage } from "@/pages/sign-in-page"
import { SignUpPage } from "@/pages/sign-up-page"
import { TriggersPage } from "@/pages/triggers-page"

export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/sign-up", element: <SignUpPage /> },
  { path: "/sign-in", element: <SignInPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/onboarding", element: <OnboardingPage /> },
  {
    path: "/app",
    element: <RoleGuard role="INVESTOR"><AppLayout /></RoleGuard>,
    children: [
      { index: true, element: <AppDashboardPage /> },
      { path: "portfolio", element: <PortfolioPage /> },
      { path: "evaluation", element: <EvaluationPage /> },
      { path: "evaluation/rebalance", element: <RebalanceReviewPage /> },
      { path: "triggers", element: <TriggersPage /> },
      { path: "activity", element: <ActivityPage /> },
      { path: "analytics", element: <AnalyticsPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
  {
    path: "/admin",
    element: <RoleGuard role="ADMIN"><AdminLayout /></RoleGuard>,
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "users", element: <AdminUsersPage /> },
      { path: "evaluations", element: <AdminEvaluationsPage /> },
      { path: "system", element: <AdminSystemPage /> },
      { path: "audit", element: <AdminAuditPage /> },
    ],
  },
])