import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, User, Calendar, Plus, Navigation } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    origin: '',
    destination: '',
    travelDateStart: '',
    travelDateEnd: '',
    travelers_count: 1,
    budget_range: 'medium',
    preferences: '',
    include_travel_options: true
  });

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? e.target.checked : value
    }));
  };

  const calculateDateRange = (start, end) => {
    if (!start || !end) return [];
    
    const dates = [];
    let currentDate = new Date(start);
    const endDate = new Date(end);
    
    while (currentDate <= endDate) {
      dates.push(currentDate.toISOString().split('T')[0]);
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return dates;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Construct the payload matching the backend schemas
    const travel_dates = calculateDateRange(formData.travelDateStart, formData.travelDateEnd);
    
    if (travel_dates.length === 0) {
      alert("Please select valid travel dates.");
      return;
    }

    const payload = {
      origin: formData.origin,
      destination: formData.destination,
      travel_dates,
      travelers_count: Number(formData.travelers_count),
      budget_range: formData.budget_range,
      preferences: formData.preferences,
      include_travel_options: formData.include_travel_options
    };

    // Navigate to Plan page with the payload
    navigate('/plan', { state: { requestData: payload } });
  };

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden bg-gradient-to-br from-brand-50 to-white">
      {/* Decorative background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-brand-200/50 blur-[80px] pointer-events-none mix-blend-multiply"></div>
      <div className="absolute bottom-[-10%] right-[-5%] w-[50%] h-[50%] rounded-full bg-blue-200/40 blur-[80px] pointer-events-none mix-blend-multiply"></div>
      
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-12 lg:py-20 flex flex-col lg:flex-row items-center gap-12 z-10 relative">
        
        {/* Left Column - Copy */}
        <div className="flex-1 text-center lg:text-left space-y-8">
          <h1 className="text-5xl lg:text-7xl font-black text-slate-900 tracking-tight leading-tight">
            Plan your next <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-indigo-600">adventure</span> with AI.
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto lg:mx-0 leading-relaxed font-light">
            TBuddy analyzes weather, routes, active events, and your budget to build a comprehensive, hour-by-hour itinerary designed just for you.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start">
            <div className="flex -space-x-4">
               {[1,2,3,4].map(i => (
                 <img key={i} className="w-12 h-12 rounded-full border-4 border-white shadow-sm" src={`https://i.pravatar.cc/100?img=${i + 10}`} alt="avatar"/>
               ))}
            </div>
            <div className="text-sm text-slate-600 font-medium">
              Join <span className="text-brand-600 font-bold">10,000+</span> travelers
            </div>
          </div>
        </div>

        {/* Right Column - Form */}
        <div className="w-full max-w-md">
          <div className="bg-white/80 backdrop-blur-xl border border-white/50 p-8 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] shadow-brand-100">
            <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-2">
              <Navigation className="text-brand-600 w-6 h-6" />
              Where to?
            </h2>
            
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-4">
                <div className="relative">
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">From</label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input 
                      required
                      name="origin"
                      value={formData.origin}
                      onChange={handleChange}
                      placeholder="e.g. New York, NY" 
                      className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none" 
                    />
                  </div>
                </div>

                <div className="relative">
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">To</label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-brand-500" />
                    <input 
                      required
                      name="destination"
                      value={formData.destination}
                      onChange={handleChange}
                      placeholder="e.g. Tokyo, Japan" 
                      className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none font-medium" 
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Start Date</label>
                  <div className="relative">
                    <input 
                      required
                      type="date"
                      name="travelDateStart"
                      value={formData.travelDateStart}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none text-sm" 
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">End Date</label>
                  <div className="relative">
                    <input 
                      required
                      type="date"
                      name="travelDateEnd"
                      value={formData.travelDateEnd}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none text-sm" 
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Travelers</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input 
                      required
                      type="number"
                      min="1"
                      max="20"
                      name="travelers_count"
                      value={formData.travelers_count}
                      onChange={handleChange}
                      className="w-full pl-9 pr-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none" 
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Budget</label>
                  <select 
                    name="budget_range"
                    value={formData.budget_range}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none appearance-none"
                  >
                    <option value="low">Budget</option>
                    <option value="medium">Standard</option>
                    <option value="high">Luxury</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Special Preferences</label>
                <textarea 
                  name="preferences"
                  value={formData.preferences}
                  onChange={handleChange}
                  placeholder="e.g. Vegetarian, accessible rooms..." 
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 rounded-xl transition-all outline-none resize-none h-20" 
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input 
                  type="checkbox" 
                  id="include_travel_options"
                  name="include_travel_options"
                  checked={formData.include_travel_options}
                  onChange={handleChange}
                  className="w-5 h-5 rounded border-slate-300 text-brand-600 focus:ring-brand-500/30"
                />
                <label htmlFor="include_travel_options" className="text-sm text-slate-600 cursor-pointer">
                  Include flights and hotels in estimate
                </label>
              </div>

              <button 
                type="submit"
                className="w-full mt-4 bg-brand-600 hover:bg-brand-700 text-white font-semibold py-4 px-6 rounded-xl shadow-lg shadow-brand-500/30 transition-all flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <span>Generate Plan</span>
                <Plus className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
}
