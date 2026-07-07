import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the upload landing state', () => {
    render(<App />);
    expect(screen.getByText(/upload a clip/i)).toBeInTheDocument();
  });
});
