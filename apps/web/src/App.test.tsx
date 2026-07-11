import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from './auth';
import App from './App';

describe('App', () => {
  it('renders the upload landing state', () => {
    render(
      <AuthContext.Provider
        value={{
          isReady: true,
          user: {
            id: 'user-id',
            email: 'person@example.com'
          },
          login: async () => undefined,
          signup: async () => undefined,
          logout: async () => undefined
        }}
      >
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    expect(screen.getByText(/track uploads, worker progress/i)).toBeInTheDocument();
  });
});
