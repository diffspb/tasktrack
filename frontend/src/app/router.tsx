import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { ProjectList } from '@/features/projects/ProjectList'
import { TaskBoard } from '@/features/tasks/TaskBoard'
import { Placeholder } from '@/shared/ui/Placeholder'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: 'projects', element: <ProjectList /> },
      { path: 'projects/:id/board',    element: <TaskBoard /> },
      { path: 'projects/:id/backlog',  element: <Placeholder title="Backlog"   phase={5} /> },
      { path: 'projects/:id/members',  element: <Placeholder title="Members"   phase={5} /> },
      { path: 'projects/:id/settings', element: <Placeholder title="Settings"  phase={5} /> },
      { path: 'dashboard',             element: <Placeholder title="Dashboard" phase={5} /> },
      { path: '*', element: <Navigate to="/projects" replace /> },
    ],
  },
])
