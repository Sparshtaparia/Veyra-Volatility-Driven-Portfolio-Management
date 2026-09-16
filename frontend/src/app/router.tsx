import { createBrowserRouter } from "react-router-dom"
import { RoleGuard } from "@/auth/role-guard"
import { AdminDashboardPage } from "@/pages/admin-dashboard-page"
import { DashboardPlaceholder } from "@/pages/dashboard-placeholder"
import { ForgotPasswordPage } from "@/pages/forgot-password-page"
import { HomePage } from "@/pages/home-page"
import { SignInPage } from "@/pages/sign-in-page"
import { SignUpPage } from "@/pages/sign-up-page"
import { InvestorDashboardPage } from "@/pages/investor-dashboard-page"

export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/sign-up", element: <SignUpPage /> },
  { path: "/sign-in", element: <SignInPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/app", element: <RoleGuard role="INVESTOR"><InvestorDashboardPage /></RoleGuard> },
  { path: "/admin", element: <RoleGuard role="ADMIN"><AdminDashboardPage /></RoleGuard> },
  { path: "/dashboard", element: <DashboardPlaceholder /> },
])
