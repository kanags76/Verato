import { createContext, useContext, useState, ReactNode } from 'react';

type ErrorContextType = {
  setError: (message: string) => void;
  clearError: () => void;
};

const ErrorContext = createContext<ErrorContextType | null>(null);

let setErrorFn: ((message: string) => void) | null = null;

export const globalSetError = (message: string) => {
  if (setErrorFn) {
    setErrorFn(message);
    setTimeout(() => setErrorFn?.(''), 5000); // clear after 5s
  }
};

export const ErrorProvider = ({ children }: { children: ReactNode }) => {
  const [error, setError] = useState<string | null>(null);
  
  setErrorFn = setError;

  return (
    <ErrorContext.Provider value={{ setError, clearError: () => setError(null) }}>
      {children}
      {error && (
        <div className="fixed top-0 left-0 w-full p-4 z-[9999]">
          <div className="bg-rose-500 text-white p-4 rounded-xl shadow-lg flex justify-between items-center max-w-lg mx-auto">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-4 font-bold">✕</button>
          </div>
        </div>
      )}
    </ErrorContext.Provider>
  );
};
