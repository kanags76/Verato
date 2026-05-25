import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { 
  KeyRound, 
  Mail, 
  User, 
  Building2, 
  Loader2, 
  CheckCircle2, 
  XCircle,
  ArrowRight
} from 'lucide-react';

interface FormErrors {
  first_name?: string;
  last_name?: string;
  email?: string;
  password?: string;
  org_name?: string;
  general?: string;
}

export const Register = () => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    password_confirmation: '',
    org_name: '',
    plan: 'individual'
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [agreed, setAgreed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<'register' | 'verify'>('register');
  const [otp, setOtp] = useState('');
  const [sessionToken, setSessionToken] = useState('');
  const { register, verifyEmail } = useAuth(); // Need to ensure useAuth provides verifyEmail
  const navigate = useNavigate();

  const validateForm = () => {
    const newErrors: FormErrors = {};
    
    if (!formData.first_name.trim()) newErrors.first_name = 'First name is required';
    if (!formData.last_name.trim()) newErrors.last_name = 'Last name is required';
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!emailRegex.test(formData.email)) {
      newErrors.email = 'Please enter a valid work email';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (formData.password !== formData.password_confirmation) {
      newErrors.password = 'Passwords do not match';
    }
    
    if (!formData.org_name.trim()) {
      newErrors.org_name = 'Organisation name is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (step === 'register') {
      if (!validateForm()) return;
      
      setIsLoading(true);
      setErrors({});
      
      try {
        const { password_confirmation, ...registerDetails } = formData;
        const response = await register(registerDetails);
        setSessionToken(response.session_token);
        setStep('verify');
      } catch (err: any) {
        if (err.response?.data) {
          setErrors({
            ...err.response.data,
            general: !err.response.data.detail ? undefined : err.response.data.detail
          });
        } else {
          setErrors({ general: 'Connection failed. Please try again later.' });
        }
      } finally {
        setIsLoading(false);
      }
    } else if (step === 'verify') {
      if (!otp.trim()) {
        setErrors({ general: 'OTP is required' });
        return;
      }
      setIsLoading(true);
      setErrors({});
      try {
        await verifyEmail(sessionToken, otp);
        navigate('/onboarding/slack');
      } catch (err: any) {
        setErrors({ general: 'Invalid OTP' });
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear field error when user types
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl"
      >
        <div className="text-center mb-8">
          <Link to="/login" className="inline-flex items-center gap-2 text-slate-400 hover:text-blue-600 transition-colors mb-6 text-xs font-black uppercase tracking-widest">
            <ArrowRight className="w-3 h-3 rotate-180" />
            Back to Sign In
          </Link>
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-200">
            <span className="text-white font-black text-2xl">V</span>
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Create your Verato Account</h1>
          <p className="text-slate-500 font-medium">Join companies driving meeting accountability.</p>
        </div>

        <Card className="p-8 shadow-2xl border-slate-200">
          <form onSubmit={handleSubmit} className="space-y-5">
                        {step === 'register' ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">First Name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        name="first_name"
                        type="text"
                        required
                        value={formData.first_name}
                        onChange={handleChange}
                        className={`w-full bg-slate-50 border ${errors.first_name ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                        placeholder="Jane"
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Last Name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        name="last_name"
                        type="text"
                        required
                        value={formData.last_name}
                        onChange={handleChange}
                        className={`w-full bg-slate-50 border ${errors.last_name ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                        placeholder="Doe"
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Work Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className={`w-full bg-slate-50 border ${errors.email ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                      placeholder="jane@company.com"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Create Password (Min 8 characters)</label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      name="password"
                      type="password"
                      required
                      value={formData.password}
                      onChange={handleChange}
                      className={`w-full bg-slate-50 border ${errors.password ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Confirm Password</label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      name="password_confirmation"
                      type="password"
                      required
                      value={formData.password_confirmation}
                      onChange={handleChange}
                      className={`w-full bg-slate-50 border ${errors.password ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                      placeholder="••••••••"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Organisation Name</label>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      name="org_name"
                      type="text"
                      required
                      value={formData.org_name}
                      onChange={handleChange}
                      className={`w-full bg-slate-50 border ${errors.org_name ? 'border-rose-300 ring-4 ring-rose-50' : 'border-slate-200 focus:border-blue-500'} rounded-xl pl-10 pr-4 py-3 text-sm transition-all focus:outline-none`}
                      placeholder="Acme Corp"
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-4">
                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Enter Activation Code sent to {formData.email}</label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 focus:border-blue-500 rounded-xl px-4 py-3 text-sm transition-all focus:outline-none text-center text-2xl tracking-[0.5em]"
                  placeholder="000000"
                />
              </div>
            )}


            {errors.general && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-3 bg-rose-50 border border-rose-100 rounded-lg flex items-start gap-3"
              >
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <p className="text-xs text-rose-700 font-bold">{errors.general}</p>
              </motion.div>
            )}

            {step === 'register' && (
              <div className="flex items-start gap-2 mt-4 text-[11px] text-slate-500 font-medium">
                <input 
                  type="checkbox" 
                  checked={agreed} 
                  onChange={(e) => setAgreed(e.target.checked)} 
                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span>
                  I agree to the <a href="https://twocents.ai/terms" target="_blank" rel="noopener noreferrer" className="text-blue-600 font-bold hover:underline">Terms of Service</a> and <a href="https://twocents.ai/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 font-bold hover:underline">Privacy Policy</a>.
                </span>
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading || (step === 'register' && !agreed)}
              className="w-full h-12 text-lg shadow-blue-500/20 mt-2"
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{step === 'register' ? 'Creating account...' : 'Verifying...'}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span>{step === 'register' ? 'Send Activation' : 'Complete Registration'}</span>
                  <ArrowRight className="w-5 h-5" />
                </div>
              )}
            </Button>
          </form>
        </Card>

        <div className="mt-8 flex items-center justify-center gap-6">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
            No credit card
          </div>
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
            Free for teams
          </div>
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
            GDPR Ready
          </div>
        </div>
      </motion.div>
    </div>
  );
};
