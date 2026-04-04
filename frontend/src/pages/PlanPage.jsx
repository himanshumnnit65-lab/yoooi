import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { 
  Loader2, 
  MapPin, 
  CalendarDays, 
  Users, 
  Map as MapIcon, 
  CloudRain, 
  Banknote,
  Navigation
} from 'lucide-react';

export default function PlanPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [planData, setPlanData] = useState(null);

  // The request object passed from the LandingPage
  const requestData = location.state?.requestData;

  useEffect(() => {
    if (!requestData) {
      navigate('/');
      return;
    }

    const fetchPlan = async () => {
      try {
        const response = await axios.post('http://localhost:8000/api/v1/plan', requestData);
        if (response.data.success) {
          setPlanData(response.data);
        } else {
          setError(response.data.message || 'An error occurred while generating the plan.');
        }
      } catch (err) {
        setError(err.message || 'Failed to connect to the backend planner.');
      } finally {
        setLoading(false);
      }
    };

    fetchPlan();
  }, [requestData, navigate]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-50 min-h-[80vh]">
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-200 flex flex-col items-center max-w-sm text-center">
          <div className="relative mb-6">
            <div className="absolute inset-0 bg-brand-200 blur-xl rounded-full animate-pulse"></div>
            <Loader2 className="w-12 h-12 text-brand-600 animate-spin relative z-10" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Crafting your itinerary...</h2>
          <p className="text-sm text-slate-500">
            Our AI agents are analyzing routes, weather, and local events to build the perfect plan for you.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="bg-red-50 border border-red-200 p-6 rounded-2xl max-w-lg text-center">
          <h3 className="text-red-800 font-bold text-lg mb-2">Trip Planning Failed</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!planData) return null;

  return (
    <div className="flex-1 bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header Summary */}
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900 mb-2 flex items-center gap-3">
              <MapPin className="text-brand-600 w-8 h-8" />
              {requestData.origin} <Navigation className="text-slate-300 w-5 h-5 inline rotate-90" /> {requestData.destination}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600 font-medium">
              <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg">
                <CalendarDays className="w-4 h-4 text-brand-500" />
                {planData.trip_summary.split(' | ')[1].replace('Travel dates: ', '')}
              </div>
              <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg">
                <Users className="w-4 h-4 text-brand-500" />
                {requestData.travelers_count} Travelers
              </div>
              <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg capitalize">
                 <Banknote className="w-4 h-4 text-brand-500" />
                {requestData.budget_range} Budget
              </div>
            </div>
          </div>
          
          <button 
            onClick={() => navigate('/')}
            className="px-5 py-2.5 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl font-medium transition-colors text-sm"
          >
            Edit Trip Details
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Itinerary Timeline */}
          <div className="lg:col-span-2 space-y-6">
            <h2 className="text-2xl font-bold text-slate-900 mb-6 border-b border-slate-200 pb-4">Daily Itinerary</h2>
            
            {!planData.itinerary || planData.itinerary.length === 0 ? (
              <p className="text-slate-500 bg-white p-6 rounded-2xl border border-slate-200 text-center">No detailed itinerary available.</p>
            ) : (
              <div className="space-y-8">
                {planData.itinerary.map((day, i) => (
                  <div key={i} className="relative pl-8 md:pl-0">
                    <div className="hidden md:block absolute left-[31px] top-10 bottom-[-32px] w-0.5 bg-slate-200"></div>
                    <div className="flex flex-col md:flex-row gap-6">
                      <div className="md:w-16 flex-shrink-0 pt-1 relative z-10 hidden md:block">
                        <div className="w-16 h-16 bg-brand-50 text-brand-700 rounded-2xl flex flex-col items-center justify-center font-bold border border-brand-100 shadow-sm">
                          <span className="text-xs uppercase tracking-wider text-brand-500/80 mb-0.5">Day</span>
                          <span className="text-xl leading-none">{day.day}</span>
                        </div>
                      </div>
                      
                      <div className="flex-1 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center md:hidden">
                          <span className="bg-brand-100 text-brand-700 px-2 py-1 rounded-md text-sm mr-3">Day {day.day}</span>
                          {day.date}
                        </h3>
                        <h3 className="font-semibold text-slate-800 mb-4 hidden md:block">{day.date}</h3>
                        
                        <div className="space-y-4">
                          {day.activities.map((activity, j) => (
                            <div key={j} className="flex gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100 hover:border-brand-200 hover:bg-brand-50/30 transition-colors">
                              <div className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-2 flex-shrink-0"></div>
                              <div>
                                <p className="text-slate-700">{activity}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                        {day.estimated_cost && (
                          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
                            <span className="text-slate-500 flex items-center gap-1.5">
                               Estimated Daily Cost: <span className="font-semibold text-slate-800">{day.estimated_cost}</span>
                            </span>
                          </div>
                        )}
                        {day.notes && (
                           <div className="mt-3 text-sm text-slate-500 bg-yellow-50 p-3 rounded-lg border border-yellow-100 italic">
                             {day.notes}
                           </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* Event Recommendations Section */}
            {planData.event_recommendations && (
              <div className="mt-12">
                <h2 className="text-2xl font-bold text-slate-900 mb-6 border-b border-slate-200 pb-4">Local Events & Activities</h2>
                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-6 rounded-2xl border border-indigo-100">
                  <h3 className="font-bold tracking-tight text-indigo-900 text-lg mb-3">TBuddy Event Recommendations</h3>
                  <p className="text-indigo-800 leading-relaxed font-medium">
                    {planData.event_recommendations}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            
            {/* Weather Widget */}
            {planData.weather && planData.weather.length > 0 && (
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-bl-full -z-0 opacity-50"></div>
                <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2 relative z-10">
                  <CloudRain className="w-5 h-5 text-blue-500" />
                  Weather Forecast
                </h3>
                <div className="space-y-3 relative z-10">
                  {planData.weather.slice(0,3).map((w, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                      <div>
                        <span className="text-sm font-semibold text-slate-700 block">{w.date}</span>
                        <span className="text-xs text-slate-500 capitalize">{w.condition}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-bold text-slate-800">{w.temperature_max}°</span>
                        <span className="text-xs text-slate-400 ml-1">/ {w.temperature_min}°</span>
                      </div>
                    </div>
                  ))}
                </div>
                {planData.weather.length > 3 && (
                   <p className="text-xs text-slate-400 text-center mt-3 pt-3 border-t border-slate-100">+ {planData.weather.length - 3} more days available</p>
                )}
              </div>
            )}

            {/* Route Summary Widget */}
            {planData.route && (
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <MapIcon className="w-5 h-5 text-emerald-500" />
                  Route Details
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center text-sm border-b border-slate-100 pb-2">
                    <span className="text-slate-500">Mode</span>
                    <span className="font-semibold text-slate-800 capitalize bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-md">{planData.route.transport_mode}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm border-b border-slate-100 pb-2">
                    <span className="text-slate-500">Distance</span>
                    <span className="font-semibold text-slate-800">{planData.route.distance}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500">Est. Duration</span>
                    <span className="font-semibold text-slate-800">{planData.route.duration}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Budget Widget */}
            {planData.budget && (
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <Banknote className="w-5 h-5 text-orange-500" />
                  Budget Breakdown
                </h3>
                <div className="text-center mb-6 py-4 bg-orange-50 rounded-xl border border-orange-100">
                  <p className="text-xs text-orange-600 font-semibold uppercase tracking-wider mb-1">Total Estimate</p>
                  <p className="text-3xl font-black text-orange-600">
                    {planData.budget.currency} {planData.budget.total.toLocaleString()}
                  </p>
                </div>
                <div className="space-y-3">
                  <BudgetRow label="Transportation" amount={planData.budget.transportation} currency={planData.budget.currency} />
                  <BudgetRow label="Accommodation" amount={planData.budget.accommodation} currency={planData.budget.currency} />
                  <BudgetRow label="Food & Dining" amount={planData.budget.food} currency={planData.budget.currency} />
                  <BudgetRow label="Activities" amount={planData.budget.activities} currency={planData.budget.currency} />
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}

function BudgetRow({ label, amount, currency }) {
  return (
    <div className="flex justify-between items-center text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-slate-800">{currency} {amount.toLocaleString()}</span>
    </div>
  );
}
