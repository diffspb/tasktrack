import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { ProjectList } from '@/features/projects/ProjectList'
import { TaskBoard } from '@/features/tasks/TaskBoard'
import { TaskBacklog } from '@/features/tasks/TaskBacklog'
import { Dashboard } from '@/features/dashboard/Dashboard'
import { Placeholder } from '@/shared/ui/Placeholder'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'projects', element: <ProjectList /> },
      { path: 'projects/:id/board',    element: <TaskBoard /> },
      { path: 'projects/:id/backlog',  element: <TaskBacklog /> },
      { path: 'projects/:id/members',  element: <Placeholder title="Members"   /> },
      { path: 'projects/:id/settings', element: <Placeholder title="Settings"  /> },
      { path: 'dashboard',             element: <Dashboard /> },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
])
