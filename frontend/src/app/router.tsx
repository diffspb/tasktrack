import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { AuthCallback } from '@/features/auth/AuthCallback'
import { ProjectList } from '@/features/projects/ProjectList'
import { ProjectSettings } from '@/features/projects/ProjectSettings'
import { GeneralSettingsPage } from '@/features/projects/GeneralSettingsPage'
import { TeamSettingsPage } from '@/features/projects/TeamSettingsPage'
import { WorkflowSettingsPage } from '@/features/projects/WorkflowSettingsPage'
import { BoardSettingsPage } from '@/features/projects/BoardSettingsPage'
import { ViewsSettingsPage } from '@/features/projects/ViewsSettingsPage'
import { ViewPage, ViewRedirect } from '@/features/projects/ViewPage'
import { TaskPage } from '@/features/tasks/TaskPage'
import { Dashboard } from '@/features/dashboard/Dashboard'
import { GanttListPage } from '@/features/timeline/GanttListPage'
import { GanttPage } from '@/features/timeline/GanttPage'
import { GanttSettingsPage } from '@/features/timeline/GanttSettingsPage'
import { GlobalSettingsLayout } from '@/features/admin/GlobalSettingsLayout'
import { LinkTypesSettingsPage } from '@/features/admin/LinkTypesSettingsPage'

export const router = createBrowserRouter([
  { path: '/auth/callback', element: <AuthCallback /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'projects',                              element: <ProjectList /> },
      { path: 'projects/:projectKey/views/:viewId',    element: <ViewPage /> },
      { path: 'projects/:projectKey/board',            element: <ViewRedirect type="kanban" /> },
      { path: 'projects/:projectKey/backlog',          element: <ViewRedirect type="backlog" /> },
      {
        path: 'projects/:projectKey/settings',
        element: <ProjectSettings />,
        children: [
          { index: true, element: <Navigate to="general" replace /> },
          { path: 'general',  element: <GeneralSettingsPage /> },
          { path: 'views',    element: <ViewsSettingsPage /> },
          { path: 'team',     element: <TeamSettingsPage /> },
          { path: 'workflow', element: <WorkflowSettingsPage /> },
          { path: 'board',    element: <BoardSettingsPage /> },
        ],
      },
      { path: 'projects/:projectKey/members', element: <Navigate to="../settings/team" replace /> },
      { path: 'tasks/:key',  element: <TaskPage /> },
      { path: 'dashboard',   element: <Dashboard /> },
      { path: 'timeline',                      element: <GanttListPage /> },
      { path: 'timeline/:ganttId',             element: <GanttPage /> },
      { path: 'timeline/:ganttId/settings',    element: <GanttSettingsPage /> },
      {
        path: 'admin/settings',
        element: <GlobalSettingsLayout />,
        children: [
          { index: true, element: <Navigate to="link-types" replace /> },
          { path: 'link-types', element: <LinkTypesSettingsPage /> },
        ],
      },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
])
