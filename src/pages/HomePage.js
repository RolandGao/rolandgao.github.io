// src/pages/HomePage.js
import MarkdownRenderer from '../components/MarkdownRenderer';

const HomePage = () => {
  return (
    <div className="home-page">
      <div className="profile-header">
        <img 
          src={process.env.PUBLIC_URL + '/profile_pic.png'} 
          alt="Profile" 
          className="profile-pic"
        />
      </div>
      <MarkdownRenderer filePath={process.env.PUBLIC_URL + '/data/home.md'} />
    </div>
  );
};

export default HomePage;