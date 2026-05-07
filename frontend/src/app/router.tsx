import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { AuthCallback } from '@/features/auth/AuthCallback'
import { ProjectList } from '@/features/projects/ProjectList'
import { ProjectSettings } from '@/features/projects/ProjectSettings'
import { GeneralSettingsPage } from '@/features/projects/GeneralSettingsPage'
import { TeamSettingsPage } from '@/features/projects/TeamSettingsPage'
import { WorkflowSettingsPage } from '@/features/projects/WorkflowSettingsPage'
import { BoardSettingsPage } from '@/features/projects/BoardSettingsPage'
import { TaskBoard } from '@/features/tasks/TaskBoard'
import { TaskBacklog } from '@/features/tasks/TaskBacklog'
import { TaskPage } from '@/features/tasks/TaskPage'
import { Dashboard } from '@/features/dashboard/Dashboard'

export const router = createBrowserRouter([
  { path: '/auth/callback', element: <AuthCallback /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'projects',             element: <ProjectList /> },
      { path: 'projects/:projectKey/board',   element: <TaskBoard /> },
      { path: 'projects/:projectKey/backlog', element: <TaskBacklog /> },
      {
        path: 'projects/:projectKey/settings',
        element: <ProjectSettings />,
        children: [
          { index: true, element: <Navigate to="general" replace /> },
          { path: 'general',  element: <GeneralSettingsPage /> },
          { path: 'team',     element: <TeamSettingsPage /> },
          { path: 'workflow', element: <WorkflowSettingsPage /> },
          { path: 'board',    element: <BoardSettingsPage /> },
        ],
      },
      { path: 'projects/:projectKey/members', element: <Navigate to="../settings/team" replace /> },
      { path: 'tasks/:key',           element: <TaskPage /> },
      { path: 'dashboard',            element: <Dashboard /> },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
])
