import { createContext, useContext, useEffect, useState } from 'react';

const DATA_URL = '/data/gobench_data/paper_results.json';
const GoBenchDataContext = createContext({ data: null, error: '' });

export const GoBenchDataProvider = ({ children }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    fetch(DATA_URL, { signal: controller.signal })
      .then(response => {
        if (!response.ok) {
          throw new Error('Unable to load the benchmark data.');
        }
        return response.json();
      })
      .then(setData)
      .catch(fetchError => {
        if (fetchError.name !== 'AbortError') {
          setError(fetchError.message);
        }
      });

    return () => controller.abort();
  }, []);

  return (
    <GoBenchDataContext.Provider value={{ data, error }}>
      {children}
    </GoBenchDataContext.Provider>
  );
};

export const useGoBenchData = () => useContext(GoBenchDataContext);
