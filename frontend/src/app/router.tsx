import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { Skeleton } from "../components/ui";
import { AccessDenied, NotFound, SessionExpired, Unavailable } from "../features/errors/ErrorPages";
import { RegisterPage, SignInPage } from "../features/auth/AuthPages";
import { FindChargersPage } from "../features/chargers/FindChargers";
import { ChargerDetailPage } from "../features/chargers/ChargerDetail";
import { DriverDashboard } from "../features/dashboard/DriverDashboard";
import { FavouritesPage } from "../features/favourites/FavouritesPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { LandingPage } from "../features/landing/LandingPage";
import { ManagerChargerPage, ManagerHomePage } from "../features/manager/ManagerPages";
import { AdminDriverPage, DriversPage } from "../features/manager/DriversPage";
import { MessagesPage } from "../features/messages/MessagesPage";
import { NotificationsPage } from "../features/notifications/NotificationsPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { VehiclesPage } from "../features/vehicles/VehiclesPage";
import { QueuePage } from "../features/queues/QueuePage";
import { AboutModelPage, InsightsPage, PredictionLabPage } from "../features/research/ResearchPages";
import type { Role } from "../lib/types";
import { SessionPage } from "../features/sessions/SessionPage";
import { Shell } from "./Shell";
import { AppProviders, useAuth } from "./providers";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, offline } = useAuth();
  const location = useLocation();
  if (loading) return <div className="p-8"><Skeleton className="h-40" /></div>;
  if (offline && !user) return <Unavailable />;
  if (!user) return <Navigate to="/sign-in" replace state={{ from: location.pathname + location.search }} />;
  return children;
}

function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role !== role) return <AccessDenied />;
  return children;
}

function Home() {
  const { user } = useAuth();
  if (user?.role === "manager") return <Navigate to="/app/manage" replace />;
  if (user?.role === "researcher") return <Navigate to="/app/research/predict" replace />;
  return <DriverDashboard />;
}

function RequireAdmin({children}: {children: ReactNode}) {
  const {user} = useAuth();
  return user?.role === "manager" && user.is_admin ? children : <AccessDenied/>;
}

function RoutesView() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/about" element={<Navigate to="/app/about" replace />} />
      <Route path="/session-expired" element={<SessionExpired />} />
      <Route path="/unavailable" element={<Unavailable />} />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route path="/app" element={<Home />} />
        <Route path="/app/chargers" element={<RequireRole role="driver"><FindChargersPage /></RequireRole>} />
        <Route path="/app/chargers/:chargerId" element={<RequireRole role="driver"><ChargerDetailPage /></RequireRole>} />
        <Route path="/app/session" element={<RequireRole role="driver"><SessionPage /></RequireRole>} />
        <Route path="/app/queue" element={<RequireRole role="driver"><QueuePage /></RequireRole>} />
        <Route path="/app/history" element={<RequireRole role="driver"><HistoryPage /></RequireRole>} />
        <Route path="/app/favourites" element={<RequireRole role="driver"><FavouritesPage /></RequireRole>} />
        <Route path="/app/messages" element={<MessagesPage />} />
        <Route path="/app/messages/:conversationId" element={<MessagesPage />} />
        <Route path="/app/notifications" element={<NotificationsPage />} />
        <Route path="/app/profile" element={<ProfilePage />} />
        <Route path="/app/vehicles" element={<RequireRole role="driver"><VehiclesPage /></RequireRole>} />
        <Route path="/app/research" element={<RequireRole role="researcher"><InsightsPage /></RequireRole>} />
        <Route path="/app/research/predict" element={<RequireRole role="researcher"><PredictionLabPage /></RequireRole>} />
        <Route path="/app/research/demo" element={<RequireRole role="researcher"><Navigate to="/app/research/predict" replace /></RequireRole>} />
        <Route path="/app/about" element={<RequireRole role="researcher"><AboutModelPage /></RequireRole>} />
        <Route path="/app/manage" element={<RequireRole role="manager"><ManagerHomePage /></RequireRole>} />
        <Route path="/app/manage/drivers" element={<RequireAdmin><DriversPage/></RequireAdmin>} />
        <Route path="/app/manage/drivers/:driverId" element={<RequireAdmin><AdminDriverPage/></RequireAdmin>} />
        <Route path="/app/manage/chargers/:chargerId" element={<RequireRole role="manager"><ManagerChargerPage /></RequireRole>} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export function App() {
  return (
    <AppProviders>
      <RoutesView />
    </AppProviders>
  );
}
